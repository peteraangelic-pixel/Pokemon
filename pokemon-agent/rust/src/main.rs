use clap::Parser;
use rayon::prelude::*;

#[derive(Parser, Debug)]
struct Args {
    #[arg(long, default_value_t=2)]
    games: usize,
}

fn main() {
    let args = Args::parse();
    println!("rust_gauntlet: games={} threads={}", args.games, rayon::current_num_threads());
    let v: Vec<i32> = (0..100).collect();
    let sum: i32 = v.par_iter().sum();
    println!("par sum 0..100 = {}", sum);
}
