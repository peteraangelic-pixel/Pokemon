"""Tests for the SDK-free ARC-AGI-3 exploration policy."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from policy import (  # noqa: E402
    ACTION_NAMES,
    BottomEdgeMeter,
    COMPLEX_ACTION,
    RESET,
    ExplorerPolicy,
    Snapshot,
    TileMazeNavigator,
    _bottom_edge_meter,
    changed_coordinates,
    connected_components,
    horizontal_hud_mask,
    masked_signature,
    normalize_action_name,
    normalize_actions,
    normalize_planes,
    optimistic_tile_path,
    rank_click_targets,
    snapshot_from_frame,
    tile_maze_view,
)


class PolicyHelpersTests(unittest.TestCase):
    def test_normalizes_protocol_actions(self) -> None:
        self.assertEqual(normalize_action_name(0), RESET)
        self.assertEqual(normalize_action_name(6), COMPLEX_ACTION)
        self.assertEqual(normalize_action_name("GameAction.ACTION3"), "ACTION3")
        self.assertIsNone(normalize_action_name(99))
        self.assertIsNone(normalize_action_name(True))
        self.assertEqual(
            normalize_actions([6, "ACTION1", 1, "GameAction.ACTION7", 99]),
            ("ACTION1", "ACTION6", "ACTION7"),
        )

    def test_normalizes_2d_and_multi_plane_frames(self) -> None:
        single = normalize_planes([[1, 2], [3, 4]])
        multi = normalize_planes([[[1, 2]], [[3, 4]]])
        self.assertEqual(single, (((1, 2), (3, 4)),))
        self.assertEqual(multi, (((1, 2),), ((3, 4),)))

        frame = SimpleNamespace(
            state=SimpleNamespace(value="NOT_FINISHED"),
            levels_completed=2,
            available_actions=[1, 6],
            frame=[[[0, 9], [0, 0]]],
        )
        snapshot = snapshot_from_frame(frame)
        self.assertEqual(snapshot.state, "NOT_FINISHED")
        self.assertEqual(snapshot.levels_completed, 2)
        self.assertEqual(snapshot.available_actions, ("ACTION1", "ACTION6"))
        self.assertEqual(snapshot.planes, (((0, 9), (0, 0)),))

    def test_components_and_diffs_are_deterministic(self) -> None:
        grid = ((0, 0, 9), (0, 1, 9))
        components = connected_components(grid)
        self.assertEqual([(component.color, component.size) for component in components], [(0, 3), (9, 2), (1, 1)])
        before = (grid,)
        after = (((0, 2, 9), (0, 1, 9)),)
        self.assertEqual(changed_coordinates(before, after), {(1, 0)})

    def test_salience_prefers_a_small_non_background_object(self) -> None:
        snapshot = Snapshot(
            state="NOT_FINISHED",
            levels_completed=0,
            available_actions=(COMPLEX_ACTION,),
            planes=(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 9), (0, 0, 0, 0)),),
        )
        targets = rank_click_targets(snapshot)
        self.assertTrue(targets)
        _, coordinate, reason = targets[0]
        self.assertEqual(coordinate, (3, 2))
        self.assertEqual(reason["kind"], "salient-component")
        self.assertEqual(reason["color"], 9)

    def test_hud_mask_ignores_outer_progress_strip_for_state_and_clicks(self) -> None:
        base = [[0 for _ in range(16)] for _ in range(16)]
        base[0][2] = 9  # A visually salient HUD pixel.
        base[4][4] = 8  # A visually salient world object.
        altered = [row[:] for row in base]
        altered[15][5] = 7
        interior_change = [row[:] for row in base]
        interior_change[5][5] = 7
        snapshot = Snapshot("NOT_FINISHED", 0, (COMPLEX_ACTION,), (tuple(map(tuple, base)),))
        hud_only = Snapshot("NOT_FINISHED", 0, (COMPLEX_ACTION,), (tuple(map(tuple, altered)),))
        world_change = Snapshot("NOT_FINISHED", 0, (COMPLEX_ACTION,), (tuple(map(tuple, interior_change)),))

        mask = horizontal_hud_mask(snapshot)
        self.assertIn((2, 0), mask)
        self.assertIn((5, 15), mask)
        self.assertEqual(masked_signature(snapshot, mask), masked_signature(hud_only, mask))
        self.assertNotEqual(masked_signature(snapshot, mask), masked_signature(world_change, mask))
        self.assertEqual(changed_coordinates(snapshot.planes, hud_only.planes, mask), set())
        targets = rank_click_targets(snapshot, excluded=mask)
        self.assertEqual(targets[0][1], (4, 4))
        self.assertTrue(all(point not in mask for _, point, _ in targets))

    def test_bottom_edge_meter_learns_a_repeated_depleting_tick(self) -> None:
        def snapshot(active_units: int) -> Snapshot:
            # The inactive meter colour also fills the row below the strip,
            # exercising the lower-row partial-run ambiguity.
            grid = [[3 for _ in range(64)] for _ in range(64)]
            # Distinct compact footer details bound the paired indicator rather
            # than allowing a uniform background to extend the candidate run.
            for column in range(1, 11):
                grid[61][column] = 5
                grid[62][column] = 5
            grid[61][12] = 5
            grid[62][12] = 5
            for column in range(13, 55):
                value = 11 if column >= 55 - active_units else 3
                grid[61][column] = value
                grid[62][column] = value
            for column in range(55, 64):
                value = 5 if column % 3 == 1 else 8
                grid[61][column] = value
                grid[62][column] = value
            return Snapshot("NOT_FINISHED", 0, (), (tuple(map(tuple, grid)),))

        meter = _bottom_edge_meter(snapshot(40).planes[0])
        self.assertIsNotNone(meter)
        assert meter is not None
        self.assertEqual((meter.row, meter.start, len(meter.values)), (61, 13, 42))

        navigator = TileMazeNavigator()
        navigator._observe_bottom_meter(snapshot(40))  # noqa: SLF001 - visual sequence setup
        navigator._observe_bottom_meter(snapshot(38))  # noqa: SLF001 - first observed tick
        self.assertIsNone(navigator._meter_actions_remaining())  # noqa: SLF001
        navigator._observe_bottom_meter(snapshot(36))  # noqa: SLF001 - repeated tick confirms direction
        self.assertEqual(navigator._meter_actions_remaining(), 18)  # noqa: SLF001
        self.assertEqual(
            navigator.meter_evidence(),
            {
                "candidate-observations": 3,
                "estimates-established": 1,
                "matching-geometry-observations": 2,
                "regular-tick-observations": 2,
            },
        )
        navigator._observe_bottom_meter(snapshot(42))  # noqa: SLF001 - full reset state
        self.assertEqual(
            (navigator._last_bottom_meter.row, navigator._last_bottom_meter.start, len(navigator._last_bottom_meter.values)),  # noqa: SLF001
            (61, 13, 42),
        )
        self.assertEqual(navigator._meter_actions_remaining(), 21)  # noqa: SLF001
        self.assertEqual(navigator.meter_evidence()["geometry-alignments"], 1)

        # A new footer placement cannot reuse the prior active colour/tick
        # estimate, even if its pixels still look meter-like.
        navigator._last_bottom_meter = BottomEdgeMeter(  # noqa: SLF001 - shifted geometry setup
            row=60,
            start=13,
            values=(11,) * 42,
        )
        navigator._observe_bottom_meter(snapshot(42))  # noqa: SLF001 - geometry update
        self.assertIsNone(navigator._meter_actions_remaining())  # noqa: SLF001
        self.assertEqual(navigator.meter_evidence()["geometry-estimate-resets"], 1)


class ExplorerPolicyTests(unittest.TestCase):
    @staticmethod
    def _snapshot(
        state: str = "NOT_FINISHED",
        actions: tuple[str, ...] = ("ACTION1", "ACTION2", "ACTION6"),
        grid: tuple[tuple[int, ...], ...] = ((0, 0, 0), (0, 9, 0), (0, 0, 0)),
        levels: int = 0,
    ) -> Snapshot:
        return Snapshot(state, levels, actions, (grid,))

    @staticmethod
    def _tile_maze_snapshot(
        avatar: tuple[int, int] = (6, 8),
        *,
        levels: int = 0,
        goal_halo: bool = False,
    ) -> Snapshot:
        """Make a visual-only 12×12 navigation fixture with no game ID hint."""
        grid = [[4 for _ in range(64)] for _ in range(64)]

        def paint(cell: tuple[int, int], rows: tuple[int, ...]) -> None:
            x = 4 + 5 * cell[0]
            y = 5 * cell[1]
            for row, color in enumerate(rows):
                for column in range(5):
                    grid[y + row][x + column] = color

        # Two non-uniform landmarks; the striped avatar renders over either
        # landmark when it arrives, as an ordinary sprite layer would.
        paint((3, 6), (3, 3, 0, 1, 3))
        paint((6, 2), (5, 9, 5, 9, 5))
        if goal_halo:
            for cell in ((5, 1), (6, 1), (7, 1), (5, 2), (7, 2), (5, 3), (6, 3), (7, 3)):
                paint(cell, (5, 9, 5, 9, 5))
        paint(avatar, (12, 12, 9, 9, 9))
        return Snapshot("NOT_FINISHED", levels, ("ACTION1", "ACTION2", "ACTION3", "ACTION4"), (tuple(map(tuple, grid)),))

    @staticmethod
    def _maze_snapshot_custom(
        avatar: tuple[int, int],
        landmarks: tuple[tuple[tuple[int, int], tuple[int, ...]], ...],
        *,
        state: str = "NOT_FINISHED",
        levels: int = 0,
    ) -> Snapshot:
        """Build a 12×12 visual tile-maze frame with caller-chosen landmarks."""
        grid = [[4 for _ in range(64)] for _ in range(64)]

        def paint(cell: tuple[int, int], rows: tuple[int, ...]) -> None:
            x = 4 + 5 * cell[0]
            y = 5 * cell[1]
            for row, color in enumerate(rows):
                for column in range(5):
                    grid[y + row][x + column] = color

        for cell, rows in landmarks:
            paint(cell, rows)
        paint(avatar, (12, 12, 9, 9, 9))
        return Snapshot(
            state,
            levels,
            ("ACTION1", "ACTION2", "ACTION3", "ACTION4"),
            (tuple(map(tuple, grid)),),
        )

    @staticmethod
    def _token_maze_snapshot(
        avatar: tuple[int, int],
        *,
        turns_to_target: int,
        walls: frozenset[tuple[int, int]] = frozenset(),
        resources: frozenset[tuple[int, int]] = frozenset(),
        controls: tuple[tuple[int, int], ...] = ((3, 6),),
        badge_foreground: int | None = None,
        target_coordinate: tuple[int, int] = (7, 2),
        meter_active_units: int | None = None,
    ) -> Snapshot:
        """Make a generic badge/control/target fixture with arbitrary colours."""
        grid = [[4 for _ in range(64)] for _ in range(64)]

        def paint(cell: tuple[int, int], glyph: tuple[tuple[int, ...], ...]) -> None:
            x = 4 + 5 * cell[0]
            y = 5 * cell[1]
            for row, values in enumerate(glyph):
                grid[y + row][x : x + 5] = values

        def rotate(glyph: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
            return tuple(tuple(glyph[4 - x][y] for x in range(5)) for y in range(5))

        target = (
            (5, 5, 5, 5, 5),
            (5, 9, 9, 9, 5),
            (5, 9, 5, 5, 5),
            (5, 9, 5, 9, 5),
            (5, 5, 5, 5, 5),
        )
        badge = target
        for _ in range((-turns_to_target) % 4):
            badge = rotate(badge)
        control = (
            (4, 4, 4, 4, 4),
            (4, 0, 4, 4, 4),
            (4, 4, 1, 1, 4),
            (4, 4, 1, 4, 4),
            (4, 4, 4, 4, 4),
        )
        for wall in walls:
            paint(wall, ((8,) * 5,) * 5)
        ring = (
            (4, 4, 4, 4, 4),
            (4, 6, 6, 6, 4),
            (4, 6, 4, 6, 4),
            (4, 6, 6, 6, 4),
            (4, 4, 4, 4, 4),
        )
        if badge_foreground is not None:
            badge = tuple(
                tuple(badge_foreground if value == 9 else value for value in row)
                for row in badge
            )
        for resource in resources:
            paint(resource, ring)
        paint(target_coordinate, target)
        for control_coordinate in controls:
            paint(control_coordinate, control)
        paint(avatar, ((12,) * 5, (12,) * 5, (9,) * 5, (9,) * 5, (9,) * 5))
        for y in range(5):
            for x in range(5):
                value = badge[y][x]
                for dy in range(2):
                    for dx in range(2):
                        grid[53 + 2 * y + dy][1 + 2 * x + dx] = value
        if meter_active_units is not None:
            for column in range(13, 55):
                value = 11 if column < 13 + meter_active_units else 3
                grid[61][column] = value
                grid[62][column] = value
            # Keep the paired strip geometrically bounded when its active run
            # shrinks, rather than letting it merge with uniform footer space.
            for column in range(55, 64):
                value = 5 if column % 3 == 1 else 8
                grid[61][column] = value
                grid[62][column] = value
        return Snapshot(
            "NOT_FINISHED",
            0,
            ("ACTION1", "ACTION2", "ACTION3", "ACTION4"),
            (tuple(map(tuple, grid)),),
        )

    def test_resets_unplayed_and_game_over(self) -> None:
        policy = ExplorerPolicy()
        initial = self._snapshot(state="NOT_PLAYED", actions=())
        self.assertEqual(policy.choose(initial).name, RESET)
        self.assertEqual(policy.choose(self._snapshot(state="GAME_OVER", actions=())).name, RESET)
        self.assertEqual(policy.token_evidence(), {"reset-terminal": 2})

    def test_policy_learns_a_terminal_landing_after_one_game_over(self) -> None:
        policy = ExplorerPolicy()
        landmark = ((11, 3), (3, 3, 0, 1, 3))
        death = self._maze_snapshot_custom(
            avatar=(10, 3), landmarks=(landmark,), state="GAME_OVER", levels=2
        )
        self.assertEqual(policy.choose(death).name, RESET)
        evidence = policy.token_evidence()
        self.assertEqual(evidence.get("terminal-landings-seen"), 1)
        self.assertEqual(evidence.get("terminal-landings-learned"), 1)
        # A second identical GAME_OVER on the same level+tile is recorded but
        # does not double-count the learned guard.
        self.assertEqual(policy.choose(death).name, RESET)
        evidence = policy.token_evidence()
        self.assertEqual(evidence.get("terminal-landings-seen"), 2)
        self.assertEqual(evidence.get("terminal-landings-learned"), 1)

    def test_terminal_landing_guard_is_isolated_per_level(self) -> None:
        policy = ExplorerPolicy()
        landmark = ((11, 3), (3, 3, 0, 1, 3))
        death_level_2 = self._maze_snapshot_custom(
            avatar=(10, 3), landmarks=(landmark,), state="GAME_OVER", levels=2
        )
        self.assertEqual(policy.choose(death_level_2).name, RESET)
        self.assertEqual(policy.token_evidence().get("terminal-landings-learned"), 1)
        # A later level with the same tile geometry must not inherit the guard:
        # the naive direct step into (10,3) remains allowed on level 3.
        live_level_3 = self._maze_snapshot_custom(
            avatar=(9, 3), landmarks=(landmark,), levels=3
        )
        proposal = policy.choose(live_level_3)
        self.assertEqual(proposal.reasoning.get("kind"), "tile-maze-navigation")
        self.assertEqual(proposal.name, "ACTION4")
        self.assertNotIn("terminal-landing-rerouted", policy.token_evidence())

    def test_policy_reroutes_away_from_a_learned_terminal_landing(self) -> None:
        policy = ExplorerPolicy()
        landmark = ((11, 3), (3, 3, 0, 1, 3))
        death = self._maze_snapshot_custom(
            avatar=(10, 3), landmarks=(landmark,), state="GAME_OVER", levels=2
        )
        # One explicit GAME_OVER landing on tile (10,3) learns the guard.
        self.assertEqual(policy.choose(death).name, RESET)
        self.assertEqual(policy.token_evidence().get("terminal-landings-learned"), 1)
        # The avatar now stands at (9,3); the naive two-step route to the only
        # landmark at (11,3) enters (10,3) first (ACTION4). The guard must
        # divert navigation around that tile instead.
        live = self._maze_snapshot_custom(avatar=(9, 3), landmarks=(landmark,), levels=2)
        proposal = policy.choose(live)
        self.assertEqual(proposal.reasoning.get("kind"), "tile-maze-navigation")
        self.assertEqual(proposal.name, "ACTION1")
        self.assertGreaterEqual(policy.token_evidence().get("terminal-landing-rerouted", 0), 1)

    def test_only_emits_advertised_action(self) -> None:
        policy = ExplorerPolicy()
        snapshot = self._snapshot(actions=("ACTION3",))
        proposal = policy.choose(snapshot)
        self.assertEqual(proposal.name, "ACTION3")

    def test_graph_returns_via_directional_inverse_before_expanding_child(self) -> None:
        policy = ExplorerPolicy()
        start = self._snapshot(actions=("ACTION1", "ACTION2"), grid=((0, 0), (0, 9)))
        middle = self._snapshot(actions=("ACTION1", "ACTION2"), grid=((0, 1), (0, 9)))

        self.assertEqual(policy.choose(start).name, "ACTION1")
        # A fresh directional successor tests its protocol inverse first. This
        # establishes a cheap route home rather than immediately walking deeper.
        self.assertEqual(policy.choose(middle).name, "ACTION2")
        # The shallow parent is reachable again and still has ACTION2 untested.
        self.assertEqual(policy.choose(start).name, "ACTION2")

    def test_graph_replays_route_to_a_scheduled_frontier(self) -> None:
        policy = ExplorerPolicy()
        start = self._snapshot(actions=("ACTION1",), grid=((0, 0), (0, 9)))
        middle = self._snapshot(actions=("ACTION1", "ACTION2"), grid=((0, 1), (0, 9)))
        frontier = self._snapshot(actions=("ACTION1", "ACTION2"), grid=((0, 2), (0, 9)))

        self.assertEqual(policy.choose(start).name, "ACTION1")
        self.assertEqual(policy.choose(middle).name, "ACTION2")  # return to start
        # Start is closed, so replay the known route to the shallow open middle.
        self.assertEqual(policy.choose(start).name, "ACTION1")
        self.assertEqual(policy.choose(middle).name, "ACTION1")
        # The fresh deeper successor similarly establishes its return route.
        self.assertEqual(policy.choose(frontier).name, "ACTION2")
        # Middle is closed; replay its known edge to frontier's remaining action.
        self.assertEqual(policy.choose(middle).name, "ACTION1")

    def test_tile_maze_view_finds_striped_avatar_and_landmark_centres(self) -> None:
        view = tile_maze_view(self._tile_maze_snapshot())
        self.assertIsNotNone(view)
        assert view is not None
        self.assertEqual(view.avatar, (6, 8))
        self.assertEqual(view.shape, (12, 12))
        self.assertIn((3, 6), [representative for representative, _ in view.landmarks])
        self.assertIn((6, 2), [representative for representative, _ in view.landmarks])

    def test_tile_maze_view_matches_edge_badge_to_rotated_board_target(self) -> None:
        view = tile_maze_view(self._token_maze_snapshot((5, 6), turns_to_target=3))
        self.assertIsNotNone(view)
        assert view is not None
        self.assertEqual(view.control_tiles, ((3, 6),))
        self.assertEqual(
            [(target.coordinate, target.quarter_turns) for target in view.token_targets],
            [((7, 2), 3)],
        )

    def test_tile_maze_view_matches_a_palette_shifted_badge_to_a_bottom_target(self) -> None:
        view = tile_maze_view(
            self._token_maze_snapshot(
                (5, 6),
                turns_to_target=2,
                badge_foreground=12,
                target_coordinate=(7, 10),
            )
        )
        self.assertIsNotNone(view)
        assert view is not None
        self.assertEqual(
            [(target.coordinate, target.quarter_turns, target.appearance_mismatches) for target in view.token_targets],
            [((7, 10), 2, 6)],
        )

    def test_tile_maze_navigator_switches_from_a_palette_to_a_rotation_control(self) -> None:
        """Separate controls are identified from visual effects, not glyph IDs."""
        navigator = TileMazeNavigator()
        controls = ((3, 6), (5, 6))
        # The nearer first control changes only the badge palette. Once its
        # aligned appearance agrees, the navigator moves to the other visible
        # control, whose first entry changes the inferred orientation.
        self.assertEqual(
            navigator.choose(
                self._token_maze_snapshot(
                    (4, 6),
                    turns_to_target=2,
                    badge_foreground=12,
                    controls=controls,
                )
            ).name,
            "ACTION3",
        )
        toward_rotation = navigator.choose(
            self._token_maze_snapshot(
                (3, 6),
                turns_to_target=2,
                badge_foreground=9,
                controls=controls,
            )
        )
        self.assertEqual(toward_rotation.name, "ACTION4")
        self.assertEqual(toward_rotation.reasoning["target"], [5, 6])
        self.assertEqual(
            navigator.choose(
                self._token_maze_snapshot(
                    (4, 6),
                    turns_to_target=2,
                    badge_foreground=9,
                    controls=controls,
                )
            ).name,
            "ACTION4",
        )
        self.assertEqual(
            navigator.choose(
                self._token_maze_snapshot(
                    (5, 6),
                    turns_to_target=1,
                    badge_foreground=9,
                    controls=controls,
                )
            ).name,
            "ACTION3",
        )
        self.assertEqual(
            navigator.choose(
                self._token_maze_snapshot(
                    (4, 6),
                    turns_to_target=1,
                    badge_foreground=9,
                    controls=controls,
                )
            ).name,
            "ACTION4",
        )
        toward_goal = navigator.choose(
            self._token_maze_snapshot(
                (5, 6),
                turns_to_target=0,
                badge_foreground=9,
                controls=controls,
            )
        )
        self.assertEqual(toward_goal.reasoning["kind"], "tile-badge-navigation")
        self.assertEqual(toward_goal.reasoning["target"], [7, 2])

    def test_tile_maze_navigator_visits_nearest_framed_resource_before_control(self) -> None:
        resources = frozenset({(2, 3), (6, 6)})
        navigator = TileMazeNavigator()
        first = navigator.choose(
            self._token_maze_snapshot((5, 6), turns_to_target=3, resources=resources)
        )
        self.assertEqual(first.reasoning["kind"], "tile-resource-navigation")
        self.assertEqual(first.reasoning["target"], [6, 6])
        after_pickup = navigator.choose(
            self._token_maze_snapshot((6, 6), turns_to_target=3, resources=frozenset({(2, 3)}))
        )
        self.assertEqual(after_pickup.reasoning["kind"], "tile-badge-navigation")
        self.assertEqual(after_pickup.reasoning["target"], [3, 6])

    def test_tile_maze_navigator_uses_remaining_resource_on_an_equal_goal_route(self) -> None:
        navigator = TileMazeNavigator()
        navigator._token_goal = (7, 2)  # noqa: SLF001 - matched visual route setup
        navigator._token_control = (3, 6)  # noqa: SLF001 - matched visual route setup
        navigator._control_entries = 3  # noqa: SLF001 - no more control cycles required
        navigator._used_resources.add((6, 6))  # noqa: SLF001 - pre-control resource consumed
        proposal = navigator.choose(
            self._token_maze_snapshot(
                (3, 6),
                turns_to_target=0,
                resources=frozenset({(3, 4)}),
            )
        )
        self.assertEqual(proposal.reasoning["kind"], "tile-resource-navigation")
        self.assertEqual(proposal.reasoning["target"], [3, 4])

    def test_tile_maze_navigator_uses_a_remaining_resource_on_an_equal_control_route(self) -> None:
        navigator = TileMazeNavigator()
        navigator._token_goal = (7, 2)  # noqa: SLF001 - matched visual route setup
        navigator._token_control = (2, 6)  # noqa: SLF001 - active compact control
        navigator._used_resources.add((6, 6))  # noqa: SLF001 - first ring consumed
        proposal = navigator.choose(
            self._token_maze_snapshot(
                (6, 6),
                turns_to_target=3,
                resources=frozenset({(4, 6)}),
                controls=((2, 6),),
            )
        )
        self.assertEqual(proposal.reasoning["kind"], "tile-resource-navigation")
        self.assertEqual(proposal.reasoning["target"], [4, 6])
        self.assertEqual(proposal.reasoning["goal"], [2, 6])

    def test_tile_maze_navigator_uses_a_reachable_detour_when_meter_is_tight(self) -> None:
        navigator = TileMazeNavigator()
        navigator._token_goal = (7, 2)  # noqa: SLF001 - matched visual route setup
        navigator._token_control = (2, 6)  # noqa: SLF001 - active compact control
        navigator._used_resources.add((6, 6))  # noqa: SLF001 - first ring consumed
        navigator._retired_controls.add((3, 6))  # noqa: SLF001 - prior control stage completed
        navigator._control_effects[(3, 6)] = (False, True)  # noqa: SLF001 - prior palette feedback
        navigator._last_bottom_meter = BottomEdgeMeter(  # noqa: SLF001 - learned visual meter
            row=61,
            start=13,
            values=(11,) * 10 + (3,) * 32,
        )
        navigator._meter_active_value = 11  # noqa: SLF001 - repeated-tick inference setup
        navigator._meter_units_per_action = 2  # noqa: SLF001 - repeated-tick inference setup
        proposal = navigator.choose(
            self._token_maze_snapshot(
                (6, 6),
                turns_to_target=3,
                resources=frozenset({(4, 4)}),
                controls=((2, 6),),
                meter_active_units=10,
            )
        )
        self.assertEqual(proposal.reasoning["kind"], "tile-resource-navigation")
        self.assertEqual(proposal.reasoning["target"], [4, 4])
        self.assertEqual(proposal.reasoning["meter_budget_actions"], 5)
        evidence = navigator.meter_evidence()
        self.assertEqual(evidence["staged-route-checks"], 1)
        self.assertEqual(evidence["meter-tight-route-checks"], 1)
        self.assertEqual(evidence["meter-resource-route-attempts"], 1)
        self.assertEqual(evidence["meter-bounded-resource-actions"], 1)
        continued = navigator.choose(
            self._token_maze_snapshot(
                (5, 6),
                turns_to_target=3,
                resources=frozenset({(4, 4)}),
                controls=((2, 6),),
                meter_active_units=8,
            )
        )
        self.assertEqual(continued.reasoning["kind"], "tile-resource-navigation")
        self.assertEqual(continued.reasoning["meter_budget_actions"], 4)

    def test_tile_maze_navigator_defers_an_over_budget_resource_without_marking_it_used(self) -> None:
        """A meter rejection is route feedback, not evidence of a pickup."""
        snapshot = self._token_maze_snapshot(
            (6, 6),
            turns_to_target=3,
            resources=frozenset({(4, 4)}),
            controls=((2, 6),),
        )
        view = tile_maze_view(snapshot)
        self.assertIsNotNone(view)
        assert view is not None
        navigator = TileMazeNavigator()
        navigator._active_resource = (4, 4)  # noqa: SLF001 - active meter-route setup
        navigator._active_resource_meter_bound = True  # noqa: SLF001 - active meter-route setup

        # Four visual tile moves are needed; a three-action meter cannot pay
        # for it. The resource remains uncollected and is deferred instead.
        self.assertIsNone(
            navigator._resource_proposal(  # noqa: SLF001 - focused route outcome
                view,
                goal=(2, 6),
                require_goal_neutral_route=False,
                max_actions_to_resource=3,
            )
        )
        self.assertNotIn((4, 4), navigator._used_resources)  # noqa: SLF001
        self.assertIsNone(navigator._active_resource)  # noqa: SLF001
        self.assertEqual(navigator._meter_deferred_resources, {(4, 4): 3})  # noqa: SLF001

        # The same or a smaller budget does not endlessly reselect it.
        self.assertIsNone(
            navigator._resource_proposal(  # noqa: SLF001 - focused route outcome
                view,
                goal=(2, 6),
                require_goal_neutral_route=False,
                max_actions_to_resource=3,
            )
        )
        # A visibly larger refill reopens the route without fabricating use.
        resumed = navigator._resource_proposal(  # noqa: SLF001 - focused route outcome
            view,
            goal=(2, 6),
            require_goal_neutral_route=False,
            max_actions_to_resource=4,
        )
        self.assertIsNotNone(resumed)
        assert resumed is not None
        self.assertEqual(resumed.reasoning["target"], [4, 4])
        self.assertEqual(resumed.reasoning["meter_budget_actions"], 4)
        self.assertNotIn((4, 4), navigator._used_resources)  # noqa: SLF001
        self.assertEqual(
            navigator.meter_evidence(),
            {
                "meter-bounded-resource-actions": 1,
                "meter-resource-deferred-candidates": 1,
                "meter-resource-deferrals": 1,
                "meter-resource-no-candidates": 1,
                "meter-resource-over-budget-candidates": 1,
                "meter-resource-retried-candidates": 1,
                "meter-resource-route-attempts": 3,
            },
        )

    def test_tile_maze_navigator_bounds_an_earlier_resource_route_when_meter_learning_arrives(self) -> None:
        """A speculative ring route cannot outrun a later learned deadline."""
        navigator = TileMazeNavigator()
        navigator._token_goal = (7, 2)  # noqa: SLF001 - matched visual route setup
        navigator._token_control = (2, 6)  # noqa: SLF001 - matched visual route setup
        navigator._active_resource = (4, 4)  # noqa: SLF001 - chosen before meter inference
        navigator._last_bottom_meter = BottomEdgeMeter(  # noqa: SLF001 - repeated-tick inference setup
            row=61,
            start=13,
            values=(11,) * 6 + (3,) * 36,
        )
        navigator._meter_active_value = 11  # noqa: SLF001 - repeated-tick inference setup
        navigator._meter_units_per_action = 2  # noqa: SLF001 - repeated-tick inference setup

        # Four tile moves remain to the ring, but the currently visible meter
        # carries only three. The navigator abandons the impossible detour and
        # resumes the matched control route without falsely consuming the ring.
        proposal = navigator.choose(
            self._token_maze_snapshot(
                (6, 6),
                turns_to_target=3,
                resources=frozenset({(4, 4)}),
                controls=((2, 6),),
                meter_active_units=6,
            )
        )
        self.assertIsNotNone(proposal)
        assert proposal is not None
        self.assertEqual(proposal.reasoning["kind"], "tile-badge-navigation")
        self.assertEqual(proposal.reasoning["target"], [2, 6])
        self.assertIsNone(navigator._active_resource)  # noqa: SLF001
        self.assertNotIn((4, 4), navigator._used_resources)  # noqa: SLF001
        self.assertEqual(navigator._meter_deferred_resources, {(4, 4): 3})  # noqa: SLF001

    def test_tile_maze_navigator_keeps_an_initial_control_probe_direct_when_meter_is_tight(self) -> None:
        navigator = TileMazeNavigator()
        navigator._token_goal = (7, 2)  # noqa: SLF001 - matched visual route setup
        navigator._token_control = (2, 6)  # noqa: SLF001 - first untested control
        navigator._used_resources.add((6, 6))  # noqa: SLF001 - first ring consumed
        navigator._last_bottom_meter = BottomEdgeMeter(  # noqa: SLF001 - learned visual meter
            row=61,
            start=13,
            values=(11,) * 10 + (3,) * 32,
        )
        navigator._meter_active_value = 11  # noqa: SLF001 - repeated-tick inference setup
        navigator._meter_units_per_action = 2  # noqa: SLF001 - repeated-tick inference setup
        proposal = navigator.choose(
            self._token_maze_snapshot(
                (6, 6),
                turns_to_target=3,
                resources=frozenset({(4, 4)}),
                controls=((2, 6),),
                meter_active_units=10,
            )
        )
        self.assertEqual(proposal.reasoning["kind"], "tile-badge-navigation")
        self.assertEqual(proposal.reasoning["target"], [2, 6])

    def test_tile_maze_navigator_keeps_a_single_effective_control_direct_when_meter_is_tight(self) -> None:
        navigator = TileMazeNavigator()
        navigator._token_goal = (7, 2)  # noqa: SLF001 - matched visual route setup
        navigator._token_control = (2, 6)  # noqa: SLF001 - control remains effective
        navigator._used_resources.add((6, 6))  # noqa: SLF001 - first ring consumed
        navigator._control_effects[(2, 6)] = (True, False)  # noqa: SLF001 - same-control feedback
        navigator._last_bottom_meter = BottomEdgeMeter(  # noqa: SLF001 - learned visual meter
            row=61,
            start=13,
            values=(11,) * 10 + (3,) * 32,
        )
        navigator._meter_active_value = 11  # noqa: SLF001 - repeated-tick inference setup
        navigator._meter_units_per_action = 2  # noqa: SLF001 - repeated-tick inference setup
        proposal = navigator.choose(
            self._token_maze_snapshot(
                (6, 6),
                turns_to_target=2,
                resources=frozenset({(4, 4)}),
                controls=((2, 6),),
                meter_active_units=10,
            )
        )
        self.assertEqual(proposal.reasoning["kind"], "tile-badge-navigation")
        self.assertEqual(proposal.reasoning["target"], [2, 6])

    def test_tile_maze_navigator_cycles_a_control_until_badge_matches_target(self) -> None:
        navigator = TileMazeNavigator()
        # The token initially needs three visually inferred quarter turns. A
        # successful entry changes it to two, then local exits/re-entries cycle
        # it without any fixed game-specific press count.
        self.assertEqual(
            navigator.choose(self._token_maze_snapshot((4, 6), turns_to_target=3)).name,
            "ACTION3",
        )
        self.assertEqual(
            navigator.choose(self._token_maze_snapshot((3, 6), turns_to_target=2)).name,
            "ACTION4",
        )
        self.assertEqual(
            navigator.choose(self._token_maze_snapshot((4, 6), turns_to_target=2)).name,
            "ACTION3",
        )
        self.assertEqual(
            navigator.choose(self._token_maze_snapshot((3, 6), turns_to_target=1)).name,
            "ACTION4",
        )
        self.assertEqual(
            navigator.choose(self._token_maze_snapshot((4, 6), turns_to_target=1)).name,
            "ACTION3",
        )
        toward_goal = navigator.choose(self._token_maze_snapshot((3, 6), turns_to_target=0))
        self.assertIsNotNone(toward_goal)
        assert toward_goal is not None
        self.assertEqual(toward_goal.reasoning["kind"], "tile-badge-navigation")
        self.assertEqual(toward_goal.reasoning["target"], [7, 2])
        self.assertEqual(
            navigator.token_evidence(),
            {
                "control-entries": 3,
                "orientation-changing-entries": 3,
                "orientation-improving-entries": 2,
                "orientation-worsening-entries": 1,
                "relations-selected": 1,
            },
        )

    def test_tile_maze_navigator_preserves_a_live_relation_after_an_unexpected_move(self) -> None:
        """A spatial discontinuity need not erase a still-visible token/control pair."""
        navigator = TileMazeNavigator()
        initial = navigator.choose(
            self._token_maze_snapshot((4, 6), turns_to_target=2, controls=((3, 6),))
        )
        self.assertIsNotNone(initial)
        assert initial is not None
        self.assertEqual(initial.reasoning["target"], [3, 6])

        # The avatar lands somewhere other than either its prior tile or the
        # one-step successor, while the selected token and control are still
        # freshly recognized at their previous lattice coordinates.
        resumed = navigator.choose(
            self._token_maze_snapshot((6, 6), turns_to_target=2, controls=((3, 6),))
        )
        self.assertIsNotNone(resumed)
        assert resumed is not None
        self.assertEqual(resumed.reasoning["kind"], "tile-badge-navigation")
        self.assertEqual(resumed.reasoning["target"], [3, 6])
        evidence = navigator.token_evidence()
        self.assertEqual(evidence["relations-selected"], 1)
        self.assertEqual(evidence["unexpected-avatar-relation-preserved"], 1)
        self.assertNotIn("unexpected-avatar-resets", evidence)

    def test_tile_maze_navigator_does_not_cycle_grace_on_non_tile_frames(self) -> None:
        """Unrelated games must not manufacture tile-view recovery state."""
        navigator = TileMazeNavigator()
        non_tile = Snapshot(
            "NOT_FINISHED",
            0,
            ("ACTION1", "ACTION2", "ACTION6"),
            (((0, 0), (0, 0)),),
        )
        for _ in range(3):
            self.assertIsNone(navigator.choose(non_tile))
        self.assertEqual(navigator.token_evidence(), {})
        self.assertEqual(navigator._view_misses, 0)  # noqa: SLF001 - bounded-state regression

    def test_tile_maze_navigator_keeps_a_live_relation_through_one_missing_frame(self) -> None:
        """A single unreadable frame yields safely without throwing away context."""
        navigator = TileMazeNavigator()
        navigator.choose(self._token_maze_snapshot((4, 6), turns_to_target=2, controls=((3, 6),)))
        missing = Snapshot(
            "NOT_FINISHED",
            0,
            ("ACTION1", "ACTION2", "ACTION3", "ACTION4"),
            (((0, 0), (0, 0)),),
        )
        self.assertIsNone(navigator.choose(missing))
        self.assertEqual(navigator.token_evidence()["view-grace-observations"], 1)

        resumed = navigator.choose(
            self._token_maze_snapshot((6, 6), turns_to_target=2, controls=((3, 6),))
        )
        self.assertIsNotNone(resumed)
        assert resumed is not None
        self.assertEqual(resumed.reasoning["target"], [3, 6])
        self.assertEqual(navigator.token_evidence()["relations-selected"], 1)

    def test_tile_maze_navigator_generalizes_a_confirmed_uniform_collision_style(self) -> None:
        snapshot = self._token_maze_snapshot(
            (4, 6),
            turns_to_target=3,
            walls=frozenset({(5, 6), (5, 5)}),
        )
        view = tile_maze_view(snapshot)
        self.assertIsNotNone(view)
        assert view is not None
        navigator = TileMazeNavigator()
        # A previous successful departure exposed uniform style 4 as walkable.
        # The next attempted move stays in place at a differently styled tile.
        navigator._last_avatar = (4, 6)  # noqa: SLF001 - transition setup
        navigator._last_action = "ACTION4"  # noqa: SLF001 - transition setup
        navigator._last_view = view  # noqa: SLF001 - transition setup
        navigator._traversable_uniform_values.add(4)  # noqa: SLF001
        navigator._observe_avatar(view)  # noqa: SLF001 - test visual evidence update
        self.assertIn(8, navigator._blocked_uniform_values)  # noqa: SLF001
        self.assertIn((5, 6), navigator._known_blocked(view))  # noqa: SLF001
        self.assertIn((5, 5), navigator._known_blocked(view))  # noqa: SLF001
        self.assertNotIn((4, 6), navigator._known_blocked(view))  # noqa: SLF001

    def test_optimistic_tile_path_replans_around_a_learned_collision(self) -> None:
        direct = optimistic_tile_path((6, 8), (3, 6), (12, 12), set())
        self.assertEqual(direct, ("ACTION3", "ACTION3", "ACTION3", "ACTION1", "ACTION1"))
        blocked = optimistic_tile_path((6, 8), (3, 6), (12, 12), {(5, 8)})
        self.assertIsNotNone(blocked)
        assert blocked is not None
        self.assertEqual(blocked[0], "ACTION1")
        self.assertNotIn("ACTION6", blocked)

    def test_tile_maze_navigator_marks_a_reached_switch_before_next_landmark(self) -> None:
        navigator = TileMazeNavigator()
        # The initial nearest landmark is the switch at (3, 6).
        self.assertEqual(navigator.choose(self._tile_maze_snapshot()).name, "ACTION3")
        for avatar in ((5, 8), (4, 8), (3, 8), (3, 7)):
            self.assertIsNotNone(navigator.choose(self._tile_maze_snapshot(avatar)))
        next_target = navigator.choose(self._tile_maze_snapshot((3, 6)))
        self.assertIsNotNone(next_target)
        assert next_target is not None
        self.assertEqual(next_target.reasoning["target"], [6, 2])

    def test_tile_maze_navigator_does_not_finish_on_goal_halo_periphery(self) -> None:
        navigator = TileMazeNavigator()
        goal = frozenset((x, y) for x in (5, 6, 7) for y in (1, 2, 3))
        # Keep the target established from an earlier observation. The avatar
        # has reached its lower visual halo, not the central enterable tile.
        navigator._active = ((6, 2), goal)  # noqa: SLF001 - state-machine regression setup
        proposal = navigator.choose(self._tile_maze_snapshot((6, 3), goal_halo=True))
        self.assertIsNotNone(proposal)
        assert proposal is not None
        self.assertEqual(proposal.name, "ACTION1")
        self.assertEqual(proposal.reasoning["target"], [6, 2])

    def test_policy_uses_tile_maze_navigation_only_when_the_visual_contract_matches(self) -> None:
        policy = ExplorerPolicy()
        proposal = policy.choose(self._tile_maze_snapshot())
        self.assertEqual(proposal.name, "ACTION3")
        self.assertEqual(proposal.reasoning["kind"], "tile-maze-navigation")
        self.assertEqual(proposal.reasoning["target"], [3, 6])

    def test_clicks_salient_target_then_does_not_repeat_same_click_on_noop(self) -> None:
        policy = ExplorerPolicy()
        snapshot = self._snapshot(actions=(COMPLEX_ACTION,))
        first = policy.choose(snapshot)
        second = policy.choose(snapshot)  # ACTION6 had no visible effect.
        self.assertEqual(first.name, COMPLEX_ACTION)
        self.assertEqual((first.x, first.y), (1, 1))
        self.assertEqual(second.name, COMPLEX_ACTION)
        self.assertNotEqual((second.x, second.y), (first.x, first.y))
        diagnostics = policy.diagnostics()[COMPLEX_ACTION]
        self.assertEqual(diagnostics["attempts"], 1)
        self.assertEqual(diagnostics["changed"], 0)

    def test_records_level_progress_and_death(self) -> None:
        policy = ExplorerPolicy()
        start = self._snapshot(actions=("ACTION1",), levels=0)
        policy.choose(start)
        progressed = self._snapshot(actions=("ACTION1",), levels=1, grid=((0, 1, 0), (0, 9, 0), (0, 0, 0)))
        policy.choose(progressed)
        died = self._snapshot(state="GAME_OVER", actions=(), levels=1, grid=((0, 1, 0), (0, 9, 0), (0, 0, 0)))
        self.assertEqual(policy.choose(died).name, RESET)
        stats = policy.diagnostics()["ACTION1"]
        self.assertEqual(stats["attempts"], 2)
        self.assertEqual(stats["level_gains"], 1)
        self.assertEqual(stats["game_overs"], 1)
        trace = policy.transition_trace()
        self.assertEqual([entry["action"] for entry in trace], ["ACTION1", "ACTION1"])
        self.assertTrue(trace[0]["changed"])
        self.assertTrue(trace[-1]["game_over"])
        self.assertEqual(trace[0]["decision_kind"], "graph-simple-frontier")
        self.assertFalse(trace[0]["meter_bounded_resource"])
        self.assertEqual(policy.decision_evidence(), {"graph-simple-frontier": 2})
        self.assertEqual(policy.transition_trace(limit=0), [])

    def test_finalize_accounts_for_last_action_once_without_proposing_again(self) -> None:
        policy = ExplorerPolicy()
        start = self._snapshot(actions=("ACTION1",), grid=((0, 0), (0, 9)))
        final = self._snapshot(actions=("ACTION1",), grid=((0, 1), (0, 9)))
        policy.choose(start)
        policy.finalize(final)
        policy.finalize(final)
        self.assertEqual(policy.diagnostics()["ACTION1"]["attempts"], 1)
        self.assertEqual(len(policy.transition_trace()), 1)
        self.assertTrue(policy.transition_trace()[0]["changed"])

    def test_action_name_catalog_has_every_protocol_action(self) -> None:
        self.assertEqual(ACTION_NAMES, ("RESET", "ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"))


if __name__ == "__main__":
    unittest.main()
