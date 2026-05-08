# Example — Rust function returning Result

A typed parser with thiserror-driven errors and `?` propagation.
Demonstrates: domain newtype, derive use, no `unwrap()` in lib code.

```rust
// crates/markets/src/symbol.rs
use thiserror::Error;

#[derive(Debug, Error, PartialEq)]
pub enum ParseSymbolError {
    #[error("symbol is empty")]
    Empty,
    #[error("symbol exceeds 10 characters")]
    TooLong,
    #[error("symbol contains a non-letter")]
    NonLetter,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Symbol(String);

impl Symbol {
    pub fn parse(input: &str) -> Result<Self, ParseSymbolError> {
        let trimmed = input.trim();
        if trimmed.is_empty() {
            return Err(ParseSymbolError::Empty);
        }
        if trimmed.chars().count() > 10 {
            return Err(ParseSymbolError::TooLong);
        }
        if !trimmed.chars().all(|c| c.is_ascii_alphabetic()) {
            return Err(ParseSymbolError::NonLetter);
        }
        Ok(Self(trimmed.to_ascii_uppercase()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_input() {
        assert_eq!(Symbol::parse("   "), Err(ParseSymbolError::Empty));
    }

    #[test]
    fn upper_cases_lower_input() {
        assert_eq!(Symbol::parse("btc").unwrap().as_str(), "BTC");
    }

    #[test]
    fn rejects_long_input() {
        assert_eq!(
            Symbol::parse("ABCDEFGHIJK"),
            Err(ParseSymbolError::TooLong)
        );
    }
}
```
