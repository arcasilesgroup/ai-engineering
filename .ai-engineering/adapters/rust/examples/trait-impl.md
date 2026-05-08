# Example — Rust trait + impl

Demonstrates: small trait at the consumer site, in-memory fake for
testing, async trait via `async_trait` (crate) or native `async fn`
in trait (Rust 1.75+).

```rust
// crates/markets/src/repo.rs
use crate::Symbol;
use async_trait::async_trait;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum RepoError {
    #[error("symbol already exists")]
    SymbolTaken,
    #[error("storage failure: {0}")]
    Storage(String),
}

#[async_trait]
pub trait MarketRepository: Send + Sync {
    async fn create(&self, symbol: &Symbol, price: f64) -> Result<(), RepoError>;
    async fn exists(&self, symbol: &Symbol) -> Result<bool, RepoError>;
}

// In-memory fake for tests — keeps the public surface honest.
#[cfg(test)]
pub mod fakes {
    use super::*;
    use std::collections::HashSet;
    use std::sync::Mutex;

    #[derive(Default)]
    pub struct InMemoryRepo {
        seen: Mutex<HashSet<String>>,
    }

    #[async_trait]
    impl MarketRepository for InMemoryRepo {
        async fn create(&self, symbol: &Symbol, _price: f64) -> Result<(), RepoError> {
            let mut g = self.seen.lock().expect("poisoned");
            if !g.insert(symbol.as_str().to_owned()) {
                return Err(RepoError::SymbolTaken);
            }
            Ok(())
        }

        async fn exists(&self, symbol: &Symbol) -> Result<bool, RepoError> {
            Ok(self.seen.lock().expect("poisoned").contains(symbol.as_str()))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::fakes::InMemoryRepo;

    #[tokio::test]
    async fn create_then_exists_is_true() {
        let repo = InMemoryRepo::default();
        let s = Symbol::parse("BTC").unwrap();
        repo.create(&s, 65000.0).await.unwrap();
        assert!(repo.exists(&s).await.unwrap());
    }

    #[tokio::test]
    async fn duplicate_create_returns_taken() {
        let repo = InMemoryRepo::default();
        let s = Symbol::parse("BTC").unwrap();
        repo.create(&s, 65000.0).await.unwrap();
        assert!(matches!(
            repo.create(&s, 65000.0).await,
            Err(RepoError::SymbolTaken)
        ));
    }
}
```
