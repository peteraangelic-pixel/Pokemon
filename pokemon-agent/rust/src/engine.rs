use libloading::{Library, Symbol};
use std::ffi::{CStr, CString};
use std::os::raw::{c_int, c_void, c_char, c_uchar};
use serde_json::Value;

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct StartData {
    pub battle_ptr: *mut c_void,
    pub error_player: c_int,
    pub error_type: c_int,
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct SerialData {
    pub json: *const c_char,
    pub data: *const c_uchar,
    pub count: c_int,
    pub select_player: c_int,
}

pub struct Engine {
    lib: Library,
    battle_ptr: *mut c_void,
}

impl Engine {
    pub fn new(lib_path: &str) -> anyhow::Result<Self> {
        unsafe {
            let lib = Library::new(lib_path)?;
            let init: Symbol<unsafe extern "C" fn()> = lib.get(b"GameInitialize")?;
            init();
            Ok(Self { lib, battle_ptr: std::ptr::null_mut() })
        }
    }

    pub fn battle_start(&mut self, deck0: &[i32], deck1: &[i32]) -> anyhow::Result<Value> {
        assert_eq!(deck0.len(), 60);
        assert_eq!(deck1.len(), 60);
        let mut cards: Vec<c_int> = Vec::with_capacity(120);
        cards.extend(deck0.iter().map(|&x| x as c_int));
        cards.extend(deck1.iter().map(|&x| x as c_int));

        unsafe {
            let func: Symbol<unsafe extern "C" fn(*const c_int) -> StartData> = self.lib.get(b"BattleStart")?;
            let start_data = func(cards.as_ptr());
            if start_data.battle_ptr.is_null() {
                anyhow::bail!("BattleStart returned null ptr, error_player={}, error_type={}", start_data.error_player, start_data.error_type);
            }
            self.battle_ptr = start_data.battle_ptr;
            self.get_battle_data()
        }
    }

    pub fn get_battle_data(&self) -> anyhow::Result<Value> {
        unsafe {
            let func: Symbol<unsafe extern "C" fn(*mut c_void) -> SerialData> = self.lib.get(b"GetBattleData")?;
            let sd = func(self.battle_ptr);
            if sd.json.is_null() {
                anyhow::bail!("GetBattleData returned null json");
            }
            let c_str = CStr::from_ptr(sd.json);
            let json_str = c_str.to_string_lossy();
            let v: Value = serde_json::from_str(&json_str)?;
            Ok(v)
        }
    }

    pub fn select(&self, indices: &[i32]) -> anyhow::Result<Value> {
        unsafe {
            let func: Symbol<unsafe extern "C" fn(*mut c_void, *const c_int, c_int) -> c_int> = self.lib.get(b"Select")?;
            let ret = func(self.battle_ptr, indices.as_ptr() as *const c_int, indices.len() as c_int);
            if ret != 0 {
                anyhow::bail!("Select returned error {}", ret);
            }
            self.get_battle_data()
        }
    }

    pub fn battle_finish(&mut self) {
        if !self.battle_ptr.is_null() {
            unsafe {
                if let Ok(func) = self.lib.get::<unsafe extern "C" fn(*mut c_void)>(b"BattleFinish") {
                    func(self.battle_ptr);
                }
            }
            self.battle_ptr = std::ptr::null_mut();
        }
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        self.battle_finish();
    }
}
