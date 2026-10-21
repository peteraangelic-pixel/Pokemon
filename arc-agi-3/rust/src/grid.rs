//! Grid kernels: segmentation of an ARC-AGI-3 frame into connected components.
//!
//! This is a port of `inference/utils/segmentation.py` from
//! <https://github.com/Tufalabs/duck-harness> (MIT licence), preserving the exact
//! output semantics so it can be dropped in as a faster kernel without changing
//! what the model sees:
//!
//! * components are 4-connected, flood-filled in reading order, so `id` is the
//!   index in top-most-left-most order;
//! * `hash` is translation-invariant (colour + shape normalised to a top-left
//!   origin), matching Python's `repr()` payload byte-for-byte;
//! * `boundary` is a clockwise Moore-neighbour contour reduced to corner points;
//! * `children` is the nesting tree (innermost encloser is the parent).

use sha1::{Digest, Sha1};
use std::collections::HashSet;

/// ARC colour-symbol mapping, index = integer colour value 0..=15.
pub const ARC_COLOR_CHARS: [u8; 16] = *b"WwgGcBMPRbSYOrNp";

const ORTH: [(isize, isize); 4] = [(-1, 0), (1, 0), (0, -1), (0, 1)];
/// Clockwise Moore-neighbour offsets, starting at NW.
const CW: [(isize, isize); 8] = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
];

fn cw_index(d: (isize, isize)) -> usize {
    CW.iter()
        .position(|&o| o == d)
        .expect("invalid Moore-neighbour offset")
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Grid {
    pub h: usize,
    pub w: usize,
    pub cells: Vec<u8>,
}

impl Grid {
    pub fn from_rows(rows: &[Vec<u8>]) -> Result<Self, String> {
        if rows.is_empty() {
            return Ok(Grid {
                h: 0,
                w: 0,
                cells: Vec::new(),
            });
        }
        let h = rows.len();
        let w = rows[0].len();
        if rows.iter().any(|r| r.len() != w) {
            return Err("grid rows must all have the same width".to_string());
        }
        let mut cells = Vec::with_capacity(h * w);
        for row in rows {
            cells.extend_from_slice(row);
        }
        Ok(Grid { h, w, cells })
    }

    pub fn get(&self, r: usize, c: usize) -> u8 {
        self.cells[r * self.w + c]
    }

    /// Most frequent cell value, i.e. the background colour. Ties go to the
    /// lowest value so the result is deterministic across platforms.
    pub fn most_common_value(&self) -> u8 {
        if self.cells.is_empty() {
            return 0;
        }
        let mut counts = [0usize; 256];
        for &v in &self.cells {
            counts[v as usize] += 1;
        }
        let mut best = 0u8;
        let mut best_n = 0usize;
        for (v, &n) in counts.iter().enumerate() {
            if n > best_n {
                best_n = n;
                best = v as u8;
            }
        }
        best
    }

    /// Letter-coded rendering, identical to `format_grid_ascii` in the Python harness.
    pub fn ascii(&self) -> String {
        if self.h == 0 {
            return "(empty grid)".to_string();
        }
        let mut out = String::with_capacity(self.h * (self.w + 1));
        for r in 0..self.h {
            for c in 0..self.w {
                let v = self.get(r, c) as usize;
                out.push(ARC_COLOR_CHARS[v.min(15)] as char);
            }
            out.push('\n');
        }
        out.pop();
        out
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    pub id: usize,
    pub color: char,
    pub hash: String,
    pub pixels: usize,
    pub boundary: Vec<(usize, usize)>,
    pub children: Vec<usize>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Segmentation {
    pub nodes: Vec<Node>,
    pub adjacency_list: Vec<(usize, usize)>,
}

impl Segmentation {
    /// Render in the same shape the Python harness hands to the model.
    pub fn to_json(&self) -> serde_json::Value {
        let nodes: Vec<serde_json::Value> = self
            .nodes
            .iter()
            .map(|n| {
                serde_json::json!({
                    "id": n.id,
                    "color": n.color.to_string(),
                    "hash": n.hash,
                    "pixels": n.pixels,
                    "boundary": n.boundary.iter().map(|(r, c)| [r, c]).collect::<Vec<_>>(),
                    "children": n.children,
                })
            })
            .collect();
        serde_json::json!({
            "nodes": nodes,
            "adjacency_list": self.adjacency_list.iter().map(|(a, b)| [a, b]).collect::<Vec<_>>(),
        })
    }
}

/// Object-aware ACTION6 proposals: bbox centre per component, then contour
/// extremes. Returns `(row, col)` pairs.
///
/// The solver uses this instead of random non-background pixels: a click-only
/// board reacts to *objects*, so one probe per object (~10-40) beats sampling
/// 4096 cells. Component order is by pixel count, descending, ties broken by
/// component id, so the output is deterministic.
pub fn object_click_candidates(
    grid: &Grid,
    limit: usize,
    min_pixels: usize,
    include_background: bool,
) -> Vec<(usize, usize)> {
    let seg = segment_layer(grid);
    let bg = ARC_COLOR_CHARS[(grid.most_common_value() as usize).min(15)] as char;

    let mut nodes: Vec<&Node> = seg
        .nodes
        .iter()
        .filter(|n| (include_background || n.color != bg) && n.pixels >= min_pixels)
        .collect();
    nodes.sort_by(|a, b| b.pixels.cmp(&a.pixels).then(a.id.cmp(&b.id)));

    let mut out: Vec<(usize, usize)> = Vec::new();
    let mut seen: HashSet<(usize, usize)> = HashSet::new();

    // pass 1: bounding-box centre of each object
    for n in nodes.iter() {
        if out.len() >= limit {
            return out;
        }
        if n.boundary.is_empty() {
            continue;
        }
        let r0 = n.boundary.iter().map(|p| p.0).min().unwrap_or(0);
        let c0 = n.boundary.iter().map(|p| p.1).min().unwrap_or(0);
        let r1 = n.boundary.iter().map(|p| p.0).max().unwrap_or(0);
        let c1 = n.boundary.iter().map(|p| p.1).max().unwrap_or(0);
        let p = ((r0 + r1) / 2, (c0 + c1) / 2);
        if seen.insert(p) {
            out.push(p);
        }
    }

    // pass 2: contour extremes, for objects whose centre is unclickable
    for n in nodes.iter() {
        if out.len() >= limit {
            return out;
        }
        if n.boundary.is_empty() {
            continue;
        }
        for p in [
            n.boundary[0],
            n.boundary[n.boundary.len() / 2],
            n.boundary[n.boundary.len() - 1],
        ] {
            if out.len() >= limit {
                return out;
            }
            if seen.insert(p) {
                out.push(p);
            }
        }
    }
    out
}

fn trace_outer_contour(
    cells: &HashSet<(usize, usize)>,
    start: (usize, usize),
) -> Vec<(usize, usize)> {
    if cells.len() == 1 {
        return vec![start];
    }
    let start_i = (start.0 as isize, start.1 as isize);
    let mut contour: Vec<(usize, usize)> = vec![start];
    let mut b = start_i;
    // West neighbour: outside the component because `start` is reading-order-min.
    let mut prev = (start_i.0, start_i.1 - 1);
    let mut second: Option<(isize, isize)> = None;

    for _ in 0..(8 * cells.len() + 16) {
        let idx = cw_index((prev.0 - b.0, prev.1 - b.1));
        let mut nxt: Option<(isize, isize)> = None;
        let mut new_prev = prev;
        for k in 1..=8usize {
            let off = CW[(idx + k) % 8];
            let cand = (b.0 + off.0, b.1 + off.1);
            if cand.0 >= 0 && cand.1 >= 0 && cells.contains(&(cand.0 as usize, cand.1 as usize)) {
                nxt = Some(cand);
                let back = CW[(idx + k - 1) % 8];
                new_prev = (b.0 + back.0, b.1 + back.1);
                break;
            }
        }
        let nxt = match nxt {
            Some(n) => n,
            None => break,
        };
        match second {
            None => second = Some(nxt),
            Some(s) => {
                if b == start_i && nxt == s {
                    break; // Jacob's stopping criterion
                }
            }
        }
        contour.push((nxt.0 as usize, nxt.1 as usize));
        prev = new_prev;
        b = nxt;
    }

    if contour.len() > 1 && contour[contour.len() - 1] == contour[0] {
        contour.pop();
    }
    contour
}

/// Reduce a traced contour loop to the points where its direction changes.
fn corner_points(contour: &[(usize, usize)]) -> Vec<(usize, usize)> {
    if contour.len() <= 2 {
        return contour.to_vec();
    }
    let m = contour.len();
    let mut corners = Vec::new();
    for i in 0..m {
        let pr = contour[(i + m - 1) % m];
        let cur = contour[i];
        let nx = contour[(i + 1) % m];
        let d_in = (
            cur.0 as isize - pr.0 as isize,
            cur.1 as isize - pr.1 as isize,
        );
        let d_out = (
            nx.0 as isize - cur.0 as isize,
            nx.1 as isize - cur.1 as isize,
        );
        if d_in != d_out {
            corners.push(cur);
        }
    }
    corners
}

/// Translation-invariant signature: colour + shape normalised to a top-left origin.
///
/// The payload deliberately reproduces Python's `repr((color, norm))` so that the
/// SHA-1 prefix is byte-identical to the reference implementation.
fn object_hash(cells: &HashSet<(usize, usize)>, color: char) -> String {
    let min_r = cells.iter().map(|c| c.0).min().unwrap_or(0);
    let min_c = cells.iter().map(|c| c.1).min().unwrap_or(0);
    let mut norm: Vec<(usize, usize)> = cells
        .iter()
        .map(|&(r, c)| (r - min_r, c - min_c))
        .collect();
    norm.sort();
    let inner = norm
        .iter()
        .map(|(r, c)| format!("({}, {})", r, c))
        .collect::<Vec<_>>()
        .join(", ");
    let payload = format!("('{}', [{}])", color, inner);
    let mut hasher = Sha1::new();
    hasher.update(payload.as_bytes());
    let digest = hasher.finalize();
    let hex = format!("{:x}", digest);
    hex[..16].to_string()
}

/// Segment a frame into 4-connected components of equal colour.
pub fn segment_layer(grid: &Grid) -> Segmentation {
    let (h, w) = (grid.h, grid.w);
    if h == 0 || w == 0 {
        return Segmentation {
            nodes: Vec::new(),
            adjacency_list: Vec::new(),
        };
    }

    // --- connected components, flood-filled in reading order ---------------
    let mut comp_id = vec![-1i64; h * w];
    let mut comp_value: Vec<u8> = Vec::new();
    let mut comp_cells: Vec<HashSet<(usize, usize)>> = Vec::new();
    let mut comp_start: Vec<(usize, usize)> = Vec::new();
    let mut stack: Vec<(usize, usize)> = Vec::new();

    for sr in 0..h {
        for sc in 0..w {
            if comp_id[sr * w + sc] != -1 {
                continue;
            }
            let value = grid.get(sr, sc);
            let cid = comp_cells.len() as i64;
            let mut cells: HashSet<(usize, usize)> = HashSet::new();
            stack.clear();
            stack.push((sr, sc));
            comp_id[sr * w + sc] = cid;
            while let Some((r, c)) = stack.pop() {
                cells.insert((r, c));
                for (dr, dc) in ORTH {
                    let nr = r as isize + dr;
                    let nc = c as isize + dc;
                    if nr < 0 || nc < 0 {
                        continue;
                    }
                    let (nr, nc) = (nr as usize, nc as usize);
                    if nr < h && nc < w && comp_id[nr * w + nc] == -1 && grid.get(nr, nc) == value {
                        comp_id[nr * w + nc] = cid;
                        stack.push((nr, nc));
                    }
                }
            }
            comp_value.push(value);
            comp_cells.push(cells);
            comp_start.push((sr, sc));
        }
    }
    let n = comp_cells.len();

    // --- adjacency: any two components sharing a 4-connected edge ----------
    let mut adj: HashSet<(usize, usize)> = HashSet::new();
    for r in 0..h {
        for c in 0..w {
            let cid = comp_id[r * w + c] as usize;
            if r + 1 < h {
                let other = comp_id[(r + 1) * w + c] as usize;
                if other != cid {
                    adj.insert((cid.min(other), cid.max(other)));
                }
            }
            if c + 1 < w {
                let other = comp_id[r * w + c + 1] as usize;
                if other != cid {
                    adj.insert((cid.min(other), cid.max(other)));
                }
            }
        }
    }
    let mut adjacency_list: Vec<(usize, usize)> = adj.into_iter().collect();
    adjacency_list.sort();

    // --- containment: flood-fill each component's complement from the border -
    let mut enclosers: Vec<HashSet<usize>> = vec![HashSet::new(); n];
    let mut reached = vec![false; h * w];
    for b in 0..n {
        for cell in reached.iter_mut() {
            *cell = false;
        }
        stack.clear();
        for r in 0..h {
            for c in [0usize, w - 1] {
                if comp_id[r * w + c] as usize != b && !reached[r * w + c] {
                    reached[r * w + c] = true;
                    stack.push((r, c));
                }
            }
        }
        for c in 0..w {
            for r in [0usize, h - 1] {
                if comp_id[r * w + c] as usize != b && !reached[r * w + c] {
                    reached[r * w + c] = true;
                    stack.push((r, c));
                }
            }
        }
        while let Some((r, c)) = stack.pop() {
            for (dr, dc) in ORTH {
                let nr = r as isize + dr;
                let nc = c as isize + dc;
                if nr < 0 || nc < 0 {
                    continue;
                }
                let (nr, nc) = (nr as usize, nc as usize);
                if nr < h && nc < w && !reached[nr * w + nc] && comp_id[nr * w + nc] as usize != b {
                    reached[nr * w + nc] = true;
                    stack.push((nr, nc));
                }
            }
        }
        for a in 0..n {
            if a == b {
                continue;
            }
            let (ar, ac) = comp_start[a];
            if !reached[ar * w + ac] {
                enclosers[a].insert(b);
            }
        }
    }

    // --- parent = innermost encloser ---------------------------------------
    let mut children: Vec<Vec<usize>> = vec![Vec::new(); n];
    for a in 0..n {
        if enclosers[a].is_empty() {
            continue;
        }
        let parent = enclosers[a]
            .iter()
            .copied()
            // `max_by_key` hands the closure a *reference* to the item.
            // Tie-break on Reverse(e) so the smallest id wins, mirroring
            // Python's `max(..., key=lambda e: (len(enclosers[e]), -e))`.
            .max_by_key(|&e| (enclosers[e].len(), std::cmp::Reverse(e)))
            .expect("enclosers[a] is non-empty");
        children[parent].push(a);
    }
    for list in children.iter_mut() {
        list.sort();
    }

    // --- nodes -------------------------------------------------------------
    let mut nodes = Vec::with_capacity(n);
    for cid in 0..n {
        let value = comp_value[cid] as usize;
        let color = ARC_COLOR_CHARS[value.min(15)] as char;
        let boundary = corner_points(&trace_outer_contour(&comp_cells[cid], comp_start[cid]));
        nodes.push(Node {
            id: cid,
            color,
            hash: object_hash(&comp_cells[cid], color),
            pixels: comp_cells[cid].len(),
            boundary,
            children: children[cid].clone(),
        });
    }

    Segmentation {
        nodes,
        adjacency_list,
    }
}

#[cfg(test)]
mod click_candidate_tests {
    use super::*;

    fn grid(rows: &[Vec<u8>]) -> Grid {
        Grid::from_rows(rows).unwrap()
    }

    #[test]
    fn one_candidate_per_object() {
        // background 5, two separate 3x3 objects
        let mut rows = vec![vec![5u8; 12]; 6];
        for r in 1..4 {
            for c in 1..4 {
                rows[r][c] = 1;
            }
        }
        for r in 1..3 {
            for c in 7..10 {
                rows[r][c] = 2;
            }
        }
        let g = grid(&rows);
        let cands = object_click_candidates(&g, 8, 1, false);
        assert!(cands.len() >= 2, "expected two clicks, got {:?}", cands);
        // the 3x3 object is bigger, so it must be proposed first
        assert_eq!(cands[0], (2, 2));
    }

    #[test]
    fn background_is_skipped_by_default() {
        let rows = vec![vec![4u8; 8]; 8];
        let g = grid(&rows);
        assert!(object_click_candidates(&g, 8, 1, false).is_empty());
        assert!(!object_click_candidates(&g, 8, 1, true).is_empty());
    }

    #[test]
    fn limit_is_respected() {
        let mut rows = vec![vec![0u8; 16]; 16];
        for i in 0..8 {
            rows[1 + i * 2][1] = 1;
        }
        let g = grid(&rows);
        assert!(object_click_candidates(&g, 3, 1, false).len() <= 3);
    }

    #[test]
    fn candidates_are_deterministic() {
        let mut rows = vec![vec![0u8; 16]; 16];
        rows[2][2] = 1;
        rows[9][11] = 2;
        rows[13][4] = 3;
        let g = grid(&rows);
        let a = object_click_candidates(&g, 8, 1, false);
        let b = object_click_candidates(&g, 8, 1, false);
        assert_eq!(a, b);
    }

    #[test]
    fn min_pixels_filters_noise() {
        let mut rows = vec![vec![0u8; 16]; 16];
        rows[0][0] = 1; // single pixel
        for r in 5..10 {
            for c in 5..10 {
                rows[r][c] = 2; // 5x5 block
            }
        }
        let g = grid(&rows);
        let cands = object_click_candidates(&g, 8, 4, false);
        assert_eq!(cands.len(), 1, "single pixel should be filtered: {:?}", cands);
        assert_eq!(cands[0], (7, 7));
    }
}

#[cfg(test)]
mod background_tests {
    use super::*;

    #[test]
    fn most_common_value_picks_background() {
        let rows = vec![
            vec![3, 3, 3, 3],
            vec![3, 1, 1, 3],
            vec![3, 3, 3, 3],
        ];
        let g = Grid::from_rows(&rows).unwrap();
        assert_eq!(g.most_common_value(), 3);
    }

    #[test]
    fn most_common_value_is_deterministic_on_ties() {
        let rows = vec![vec![7, 2, 7, 2]];
        let g = Grid::from_rows(&rows).unwrap();
        assert_eq!(g.most_common_value(), 2);
    }

    #[test]
    fn most_common_value_on_empty_grid() {
        let g = Grid::from_rows(&[]).unwrap();
        assert_eq!(g.most_common_value(), 0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn grid(rows: Vec<Vec<u8>>) -> Grid {
        Grid::from_rows(&rows).unwrap()
    }

    #[test]
    fn single_component() {
        let g = grid(vec![vec![1, 1], vec![1, 1]]);
        let s = segment_layer(&g);
        assert_eq!(s.nodes.len(), 1);
        assert_eq!(s.nodes[0].pixels, 4);
        assert_eq!(s.nodes[0].color, 'w'); // index 1 -> "WwgGc..."[1]
        assert!(s.adjacency_list.is_empty());
    }

    #[test]
    fn two_components_are_adjacent() {
        let g = grid(vec![vec![1, 1, 2], vec![1, 1, 2]]);
        let s = segment_layer(&g);
        assert_eq!(s.nodes.len(), 2);
        assert_eq!(s.adjacency_list, vec![(0, 1)]);
    }

    #[test]
    fn diagonal_components_are_not_adjacent() {
        let g = grid(vec![vec![1, 2], vec![2, 1]]);
        let s = segment_layer(&g);
        // four 1-cell components, all diagonally touching -> 4-connected pairs exist
        assert_eq!(s.nodes.len(), 4);
        assert_eq!(s.adjacency_list, vec![(0, 1), (0, 2), (1, 3), (2, 3)]);
    }

    #[test]
    fn hash_is_translation_invariant() {
        let a = grid(vec![vec![0, 3, 3, 0], vec![0, 3, 3, 0]]);
        let b = grid(vec![vec![0, 0, 0, 0], vec![0, 3, 3, 0], vec![0, 3, 3, 0]]);
        let sa = segment_layer(&a);
        let sb = segment_layer(&b);
        let ha = sa
            .nodes
            .iter()
            .find(|n| n.color == ARC_COLOR_CHARS[3] as char)
            .unwrap();
        let hb = sb
            .nodes
            .iter()
            .find(|n| n.color == ARC_COLOR_CHARS[3] as char)
            .unwrap();
        assert_eq!(ha.hash, hb.hash);
        assert_eq!(ha.pixels, 4);
    }

    #[test]
    fn hash_is_shape_sensitive() {
        let line = segment_layer(&grid(vec![vec![3, 3, 3, 3]]));
        let block = segment_layer(&grid(vec![vec![3, 3], vec![3, 3]]));
        assert_ne!(line.nodes[0].hash, block.nodes[0].hash);
    }

    #[test]
    fn nesting_produces_children() {
        // 5x5 ring of colour 1 enclosing a single cell of colour 2
        let g = grid(vec![
            vec![1, 1, 1, 1, 1],
            vec![1, 1, 1, 1, 1],
            vec![1, 1, 2, 1, 1],
            vec![1, 1, 1, 1, 1],
            vec![1, 1, 1, 1, 1],
        ]);
        let s = segment_layer(&g);
        let ring = s.nodes.iter().find(|n| n.color == ARC_COLOR_CHARS[1] as char).unwrap();
        let inner = s.nodes.iter().find(|n| n.color == ARC_COLOR_CHARS[2] as char).unwrap();
        assert_eq!(ring.pixels, 24);
        assert_eq!(inner.pixels, 1);
        assert_eq!(ring.children, vec![inner.id]);
        assert!(inner.children.is_empty());
    }

    #[test]
    fn ascii_matches_python_layout() {
        let g = grid(vec![vec![0, 1], vec![2, 3]]);
        assert_eq!(g.ascii(), "Ww\ngG");
    }

    #[test]
    fn empty_grid_is_handled() {
        let g = Grid::from_rows(&[]).unwrap();
        let s = segment_layer(&g);
        assert!(s.nodes.is_empty());
    }
}

/// Cross-validation against the reference Python implementation.
///
/// Every vector below was produced by running `inference/utils/segmentation.py`
/// from <https://github.com/Tufalabs/duck-harness> (MIT) on these exact grids.
/// If this test fails, the Rust kernel has diverged from what the Python harness
/// would have told the model — which would silently change agent behaviour.
#[cfg(test)]
mod reference_vectors {
    use super::*;

    fn expect(
        name: &str,
        rows: Vec<Vec<u8>>,
        want_nodes: Vec<(&str, &str, usize, Vec<usize>)>,
        want_adj: Vec<(usize, usize)>,
    ) {
        let g = Grid::from_rows(&rows).unwrap();
        let s = segment_layer(&g);
        let got_nodes: Vec<(char, &str, usize, Vec<usize>)> = s
            .nodes
            .iter()
            .map(|n| (n.color, n.hash.as_str(), n.pixels, n.children.clone()))
            .collect();
        let want_owned: Vec<(char, &str, usize, Vec<usize>)> = want_nodes
            .into_iter()
            .map(|(c, h, p, ch)| (c.chars().next().unwrap(), h, p, ch))
            .collect();
        assert_eq!(got_nodes, want_owned, "node mismatch for case `{}`", name);
        assert_eq!(s.adjacency_list, want_adj, "adjacency mismatch for case `{}`", name);
    }

    #[test]
    fn reference_single_block() {
        expect(
            "single",
            vec![vec![1, 1], vec![1, 1]],
            vec![("w", "12a4dfc9a2aee3e1", 4, vec![])],
            vec![],
        );
    }

    #[test]
    fn reference_two_adjacent_components() {
        expect(
            "two_adj",
            vec![vec![1, 1, 2], vec![1, 1, 2]],
            vec![
                ("w", "12a4dfc9a2aee3e1", 4, vec![]),
                ("g", "e012901bd05b83f5", 2, vec![]),
            ],
            vec![(0, 1)],
        );
    }

    #[test]
    fn reference_diagonal_four_components() {
        // Diagonal neighbours are 4-disconnected: four separate 1-cell components.
        expect(
            "diag",
            vec![vec![1, 2], vec![2, 1]],
            vec![
                ("w", "ef8a692d7922fb97", 1, vec![]),
                ("g", "e92aa78a5ec1328e", 1, vec![]),
                ("g", "e92aa78a5ec1328e", 1, vec![]),
                ("w", "ef8a692d7922fb97", 1, vec![]),
            ],
            vec![(0, 1), (0, 2), (1, 3), (2, 3)],
        );
    }

    #[test]
    fn reference_translation_invariance() {
        // Same 2x2 block of colour 3 in two different positions -> identical hash.
        expect(
            "shift_a",
            vec![vec![0, 3, 3, 0], vec![0, 3, 3, 0]],
            vec![
                ("W", "42c5550fe7b33f94", 2, vec![]),
                ("G", "6d081f3b47e44da2", 4, vec![]),
                ("W", "42c5550fe7b33f94", 2, vec![]),
            ],
            vec![(0, 1), (1, 2)],
        );
        expect(
            "shift_b",
            vec![vec![0, 0, 0, 0], vec![0, 3, 3, 0], vec![0, 3, 3, 0]],
            vec![
                ("W", "f1c5b8d99eff4d55", 8, vec![]),
                ("G", "6d081f3b47e44da2", 4, vec![]),
            ],
            vec![(0, 1)],
        );
    }

    #[test]
    fn reference_shape_sensitivity() {
        // A 1x4 line and a 2x2 block have the same pixel count but different hashes.
        expect(
            "line",
            vec![vec![3, 3, 3, 3]],
            vec![("G", "640f0337395ee275", 4, vec![])],
            vec![],
        );
        expect(
            "block",
            vec![vec![3, 3], vec![3, 3]],
            vec![("G", "6d081f3b47e44da2", 4, vec![])],
            vec![],
        );
    }

    #[test]
    fn reference_nesting_children() {
        // 5x5 ring of colour 1 encloses a single cell of colour 2.
        expect(
            "ring",
            vec![
                vec![1, 1, 1, 1, 1],
                vec![1, 1, 1, 1, 1],
                vec![1, 1, 2, 1, 1],
                vec![1, 1, 1, 1, 1],
                vec![1, 1, 1, 1, 1],
            ],
            vec![
                ("w", "6363e77918119646", 24, vec![1]),
                ("g", "e92aa78a5ec1328e", 1, vec![]),
            ],
            vec![(0, 1)],
        );
    }

    /// Boundaries are the trickiest part to port (Moore-neighbour tracing plus
    /// corner reduction), so they get their own explicit vectors.
    #[test]
    fn reference_boundaries() {
        let g = Grid::from_rows(&[vec![1, 1], vec![1, 1]]).unwrap();
        let s = segment_layer(&g);
        assert_eq!(s.nodes[0].boundary, vec![(0, 0), (0, 1), (1, 1), (1, 0)]);

        let g = Grid::from_rows(&[vec![3, 3, 3, 3]]).unwrap();
        let s = segment_layer(&g);
        assert_eq!(s.nodes[0].boundary, vec![(0, 0), (0, 3)]);

        let g = Grid::from_rows(&[
            vec![0, 0, 0, 0],
            vec![0, 3, 3, 0],
            vec![0, 3, 3, 0],
        ])
        .unwrap();
        let s = segment_layer(&g);
        // Ring-ish shape: the corner-reduced contour of the 8-cell background.
        assert_eq!(
            s.nodes[0].boundary,
            vec![(0, 0), (0, 3), (2, 3), (1, 3), (0, 2), (0, 1), (1, 0), (2, 0)]
        );
        assert_eq!(s.nodes[1].boundary, vec![(1, 1), (1, 2), (2, 2), (2, 1)]);
    }
}
