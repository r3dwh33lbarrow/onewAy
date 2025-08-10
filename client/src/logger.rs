use chrono::Local;
use crossbeam_channel::{Sender, unbounded};
use once_cell::sync::OnceCell;
use std::{fmt, thread};

#[derive(Debug, Clone, Copy)]
pub enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
    Fatal,
}

impl fmt::Display for LogLevel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            LogLevel::Debug => "DEBUG",
            LogLevel::Info => "INFO",
            LogLevel::Warn => "WARN",
            LogLevel::Error => "ERROR",
            LogLevel::Fatal => "FATAL",
        };
        write!(f, "{s}")
    }
}

#[derive(Debug)]
struct LogRecord {
    level: LogLevel,
    message: String,
    timestamp: String,
}

pub struct Logger {
    tx: Sender<LogRecord>, // crossbeam Sender is Send + Sync + Clone
}

static LOGGER: OnceCell<Logger> = OnceCell::new();

pub fn init_logger() {
    if LOGGER.get().is_some() {
        return;
    }

    let (tx, rx) = unbounded::<LogRecord>();

    thread::Builder::new()
        .name("logger-writer".into())
        .spawn(move || {
            for rec in rx.iter() {
                // [LOG_LEVEL] [%d/%m/%Y %H:%M:%S] - message
                println!("[{}] [{}] - {}", rec.level, rec.timestamp, rec.message);
            }
        })
        .expect("Failed to spawn logger thread");

    let _ = LOGGER.set(Logger { tx });
}

fn ensure_init() {
    if LOGGER.get().is_none() {
        init_logger();
    }
}

pub fn log(level: LogLevel, message: impl Into<String>) {
    ensure_init();
    if let Some(logger) = LOGGER.get() {
        let ts = Local::now().format("%d/%m/%Y %H:%M:%S").to_string();
        let _ = logger.tx.send(LogRecord {
            level,
            message: message.into(),
            timestamp: ts,
        });
    }
}

#[macro_export]
macro_rules! debug {
    ($($arg:tt)*) => {
        $crate::log($crate::LogLevel::Debug, format!($($arg)*));
    };
}
#[macro_export]
macro_rules! info {
    ($($arg:tt)*) => {
        $crate::log($crate::LogLevel::Info, format!($($arg)*));
    };
}
#[macro_export]
macro_rules! warn {
    ($($arg:tt)*) => {
        $crate::log($crate::LogLevel::Warn, format!($($arg)*));
    };
}
#[macro_export]
macro_rules! error {
    ($($arg:tt)*) => {
        $crate::log($crate::LogLevel::Error, format!($($arg)*));
    };
}
#[macro_export]
macro_rules! fatal {
    ($($arg:tt)*) => {
        $crate::log($crate::LogLevel::Fatal, format!($($arg)*));
    };
}
