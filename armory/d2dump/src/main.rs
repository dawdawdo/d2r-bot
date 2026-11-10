use d2s::{D2Save, D2StashSave};
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let b = std::fs::read(&a[2]).unwrap();
    let j = if a[1] == "c" { serde_json::to_string(&D2Save::from_bytes(&b).unwrap()).unwrap() }
            else { serde_json::to_string(&D2StashSave::from_bytes(&b).unwrap()).unwrap() };
    println!("{}", j);
}
