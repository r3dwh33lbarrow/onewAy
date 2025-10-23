use chrono::Local;
use colored::Colorize;
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
    tx: Sender<LogRecord>,
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
                let level_str = match rec.level {
                    LogLevel::Debug => format!("{}", rec.level).bright_black(),
                    LogLevel::Info => format!("{}", rec.level).bright_blue(),
                    LogLevel::Warn => format!("{}", rec.level).yellow(),
                    LogLevel::Error => format!("{}", rec.level).bright_red(),
                    LogLevel::Fatal => format!("{}", rec.level).on_red().white().bold(),
                };

                let timestamp = rec.timestamp.dimmed();

                let output = format!("[{}] [{}] - {}", level_str, timestamp, rec.message);

                match rec.level {
                    LogLevel::Error | LogLevel::Fatal => {
                        eprintln!("{}", output);
                    }
                    _ => {
                        println!("{}", output);
                    }
                }
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
    // In release mode, disable logging unless output_override is enabled
    #[cfg(not(debug_assertions))]
    {
        if !crate::config::CONFIG.output_override.unwrap_or(false) {
            return;
        }
    }

    // Filter DEBUG level messages if debug is false (applies to both debug and release modes)
    if matches!(level, LogLevel::Debug) && !crate::config::CONFIG.debug.unwrap_or(false) {
        return;
    }

    // Perform the actual logging (works in both debug and release if we get here)
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
        $crate::logger::log($crate::logger::LogLevel::Debug, format!($($arg)*));
    };
}
#[macro_export]
macro_rules! info {
    ($($arg:tt)*) => {
        $crate::logger::log($crate::logger::LogLevel::Info, format!($($arg)*));
    };
}
#[macro_export]
macro_rules! warn {
    ($($arg:tt)*) => {
        $crate::logger::log($crate::logger::LogLevel::Warn, format!($($arg)*));
    };
}
#[macro_export]
macro_rules! error {
    ($($arg:tt)*) => {
        $crate::logger::log($crate::logger::LogLevel::Error, format!($($arg)*));
    };
}
#[macro_export]
macro_rules! fatal {
    ($($arg:tt)*) => {
        $crate::logger::log($crate::logger::LogLevel::Fatal, format!($($arg)*));
    };
}
