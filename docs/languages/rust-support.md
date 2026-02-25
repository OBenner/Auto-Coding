# Rust Language Support

Auto Code provides first-class support for Rust development with idiomatic code generation, framework detection, security scanning, and testing integration.

## Table of Contents

- [Setup](#setup)
  - [Rust Installation](#rust-installation)
  - [Project Setup](#project-setup)
  - [Dependency Management](#dependency-management)
- [Supported Frameworks](#supported-frameworks)
- [Idiomatic Patterns](#idiomatic-patterns)
  - [Ownership and Borrowing](#ownership-and-borrowing)
  - [Error Handling](#error-handling)
  - [Pattern Matching](#pattern-matching)
  - [Traits and Generics](#traits-and-generics)
  - [Async/Await](#asyncawait)
  - [Collections](#collections)
  - [Smart Pointers](#smart-pointers)
- [Testing](#testing)
  - [Test Patterns](#test-patterns)
  - [Running Tests](#running-tests)
  - [Benchmarking](#benchmarking)
- [Security](#security)
  - [Security Scanners](#security-scanners)
  - [Common Vulnerabilities](#common-vulnerabilities)
  - [Best Practices](#best-practices)
- [Framework-Specific Patterns](#framework-specific-patterns)
  - [Actix-web](#actix-web)
  - [Rocket](#rocket)
  - [Axum](#axum)
  - [Tokio](#tokio)
- [Code Generation](#code-generation)

---

## Setup

### Rust Installation

Install Rust via rustup (official installer):

**All platforms:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Windows:**
Download and run [rustup-init.exe](https://rustup.rs/) from the official website.

**Verify installation:**
```bash
rustc --version
cargo --version
```

**Update Rust:**
```bash
rustup update
```

**Install stable, beta, or nightly:**
```bash
rustup install stable
rustup install nightly
rustup default stable
```

### Project Setup

Create a new Rust project:

```bash
# Create binary project
cargo new my-rust-project
cd my-rust-project

# Create library project
cargo new --lib my-rust-lib

# Run the project
cargo run

# Build release version
cargo build --release
```

**Project structure:**
```text
my-rust-project/
├── Cargo.toml          # Project manifest
├── Cargo.lock          # Dependency lock file
└── src/
    └── main.rs         # Application entrypoint
```

**Library structure:**
```text
my-rust-lib/
├── Cargo.toml
└── src/
    └── lib.rs          # Library root
```

### Dependency Management

**Add dependencies in `Cargo.toml`:**
```toml
[dependencies]
tokio = { version = "1.35", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
actix-web = "4.4"
```

**Add development dependencies:**
```toml
[dev-dependencies]
mockito = "1.2"
criterion = "0.5"
```

**Add dependencies via command line:**
```bash
cargo add tokio --features full
cargo add serde --features derive
```

**Update dependencies:**
```bash
cargo update
```

**Check for outdated dependencies:**
```bash
cargo install cargo-outdated
cargo outdated
```

---

## Supported Frameworks

Auto Code detects Rust crates and provides idiomatic patterns. Crates marked **Auto-detected** are identified automatically; others are recognized when specified.

| Framework / Crate | Detection | Auto-detected | Use Case |
|-------------------|-----------|:---:|----------|
| **Actix-web** | `Cargo.toml` contains `actix-web` | ✅ | High-performance async web framework |
| **Rocket** | `Cargo.toml` contains `rocket` | ✅ | Type-safe web framework |
| **Axum** | `Cargo.toml` contains `axum` | ✅ | Ergonomic web framework built on Tokio |
| **Warp** | `Cargo.toml` contains `warp` | ✅ | Composable web server framework |
| **Tide** | `Cargo.toml` contains `tide` | ✅ | Minimal and pragmatic web framework |
| **Poem** | `Cargo.toml` contains `poem` | ✅ | Full-featured web framework |
| **Tokio** | `Cargo.toml` contains `tokio` | — | Async runtime for Rust |
| **async-std** | `Cargo.toml` contains `async-std` | — | Alternative async runtime |
| **Diesel** | `Cargo.toml` contains `diesel` | — | Safe, extensible ORM and query builder |
| **SQLx** | `Cargo.toml` contains `sqlx` | — | Async SQL toolkit |
| **Serde** | `Cargo.toml` contains `serde` | — | Serialization/deserialization framework |

---

## Idiomatic Patterns

Auto Code generates idiomatic Rust code following community best practices.

### Ownership and Borrowing

**Ownership transfer:**
```rust
fn take_ownership(s: String) {
    println!("{}", s);
}

let s = String::from("hello");
take_ownership(s);
// s is no longer valid here
```

**Borrowing (immutable):**
```rust
fn borrow(s: &String) {
    println!("{}", s);
}

let s = String::from("hello");
borrow(&s);
// s is still valid here
```

**Mutable borrowing:**
```rust
fn mutate(s: &mut String) {
    s.push_str(", world");
}

let mut s = String::from("hello");
mutate(&mut s);
println!("{}", s);  // "hello, world"
```

**Lifetime annotations:**
```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() {
        x
    } else {
        y
    }
}

let s1 = String::from("long string");
let s2 = String::from("short");
let result = longest(&s1, &s2);
```

### Error Handling

**Result type:**
```rust
use std::fs::File;
use std::io::Read;

fn read_file(path: &str) -> Result<String, std::io::Error> {
    let mut file = File::open(path)?;
    let mut contents = String::new();
    file.read_to_string(&mut contents)?;
    Ok(contents)
}
```

**Custom error types:**
```rust
use std::fmt;

#[derive(Debug)]
pub enum AppError {
    NotFound(String),
    InvalidInput(String),
    Internal(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            AppError::NotFound(msg) => write!(f, "Not found: {}", msg),
            AppError::InvalidInput(msg) => write!(f, "Invalid input: {}", msg),
            AppError::Internal(msg) => write!(f, "Internal error: {}", msg),
        }
    }
}

impl std::error::Error for AppError {}
```

**Error conversion with thiserror:**
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("not found: {0}")]
    NotFound(String),

    #[error("invalid input: {0}")]
    InvalidInput(String),
}
```

**Option handling:**
```rust
fn find_user(id: u32) -> Option<User> {
    // Return Some(user) or None
}

// Using if let
if let Some(user) = find_user(1) {
    println!("Found: {}", user.name);
}

// Using match
match find_user(1) {
    Some(user) => println!("Found: {}", user.name),
    None => println!("User not found"),
}

// Using unwrap_or
let user = find_user(1).unwrap_or(default_user);
```

### Pattern Matching

**Basic match:**
```rust
let number = 3;

match number {
    1 => println!("one"),
    2 | 3 => println!("two or three"),
    4..=10 => println!("four through ten"),
    _ => println!("something else"),
}
```

**Matching enums:**
```rust
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(i32, i32, i32),
}

fn process_message(msg: Message) {
    match msg {
        Message::Quit => println!("Quit"),
        Message::Move { x, y } => println!("Move to ({}, {})", x, y),
        Message::Write(text) => println!("Write: {}", text),
        Message::ChangeColor(r, g, b) => println!("Color: ({}, {}, {})", r, g, b),
    }
}
```

**Destructuring:**
```rust
let point = (3, 5);
let (x, y) = point;

let Person { name, age } = person;

// In function parameters
fn print_coordinates(&(x, y): &(i32, i32)) {
    println!("({}, {})", x, y);
}
```

### Traits and Generics

**Defining traits:**
```rust
pub trait Summary {
    fn summarize(&self) -> String;

    // Default implementation
    fn author(&self) -> String {
        String::from("Unknown")
    }
}
```

**Implementing traits:**
```rust
pub struct Article {
    pub title: String,
    pub content: String,
}

impl Summary for Article {
    fn summarize(&self) -> String {
        format!("{}: {}", self.title, &self.content[..50])
    }
}
```

**Generic functions:**
```rust
fn largest<T: PartialOrd>(list: &[T]) -> &T {
    let mut largest = &list[0];

    for item in list {
        if item > largest {
            largest = item;
        }
    }

    largest
}
```

**Generic structs:**
```rust
pub struct Point<T> {
    pub x: T,
    pub y: T,
}

impl<T> Point<T> {
    pub fn new(x: T, y: T) -> Self {
        Point { x, y }
    }
}
```

**Trait bounds:**
```rust
fn print_info<T: Display + Clone>(item: T) {
    println!("{}", item);
}

// Where clause for complex bounds
fn some_function<T, U>(t: &T, u: &U) -> i32
where
    T: Display + Clone,
    U: Clone + Debug,
{
    // implementation
}
```

### Async/Await

**Async functions:**
```rust
use tokio;

async fn fetch_data(url: &str) -> Result<String, reqwest::Error> {
    let response = reqwest::get(url).await?;
    let body = response.text().await?;
    Ok(body)
}

#[tokio::main]
async fn main() {
    match fetch_data("https://api.example.com/data").await {
        Ok(data) => println!("Data: {}", data),
        Err(e) => eprintln!("Error: {}", e),
    }
}
```

**Concurrent execution:**
```rust
use tokio;

async fn task1() -> String {
    // async work
    "task1 result".to_string()
}

async fn task2() -> String {
    // async work
    "task2 result".to_string()
}

#[tokio::main]
async fn main() {
    // Run tasks concurrently
    let (result1, result2) = tokio::join!(task1(), task2());

    println!("Results: {}, {}", result1, result2);
}
```

**Async streams:**
```rust
use tokio_stream::StreamExt;

async fn process_stream() {
    let mut stream = tokio_stream::iter(vec![1, 2, 3, 4, 5]);

    while let Some(value) = stream.next().await {
        println!("Value: {}", value);
    }
}
```

**Spawning tasks:**
```rust
use tokio;

#[tokio::main]
async fn main() {
    let handle = tokio::spawn(async {
        // background work
        42
    });

    let result = handle.await.unwrap();
    println!("Result: {}", result);
}
```

### Collections

**Vectors:**
```rust
let mut vec = Vec::new();
vec.push(1);
vec.push(2);

let vec = vec![1, 2, 3, 4, 5];

for item in &vec {
    println!("{}", item);
}

// Iterators
let doubled: Vec<i32> = vec.iter().map(|x| x * 2).collect();
let sum: i32 = vec.iter().sum();
```

**HashMaps:**
```rust
use std::collections::HashMap;

let mut map = HashMap::new();
map.insert(String::from("key"), 42);

// Get value
if let Some(value) = map.get("key") {
    println!("Value: {}", value);
}

// Iterate
for (key, value) in &map {
    println!("{}: {}", key, value);
}

// Entry API
map.entry(String::from("key")).or_insert(0);
```

**HashSets:**
```rust
use std::collections::HashSet;

let mut set = HashSet::new();
set.insert(1);
set.insert(2);

if set.contains(&1) {
    println!("Set contains 1");
}

// Set operations
let set1: HashSet<_> = [1, 2, 3].iter().collect();
let set2: HashSet<_> = [2, 3, 4].iter().collect();

let union: HashSet<_> = set1.union(&set2).collect();
let intersection: HashSet<_> = set1.intersection(&set2).collect();
```

### Smart Pointers

**Box (heap allocation):**
```rust
let b = Box::new(5);
println!("b = {}", b);

// Recursive types
enum List {
    Cons(i32, Box<List>),
    Nil,
}
```

**Rc (reference counting):**
```rust
use std::rc::Rc;

let a = Rc::new(5);
let b = Rc::clone(&a);
let c = Rc::clone(&a);

println!("count = {}", Rc::strong_count(&a));  // 3
```

**Arc (atomic reference counting for threads):**
```rust
use std::sync::Arc;
use std::thread;

let data = Arc::new(vec![1, 2, 3]);

let handles: Vec<_> = (0..3).map(|_| {
    let data = Arc::clone(&data);
    thread::spawn(move || {
        println!("{:?}", data);
    })
}).collect();

for handle in handles {
    handle.join().unwrap();
}
```

**RefCell (interior mutability):**
```rust
use std::cell::RefCell;

let data = RefCell::new(5);

{
    let mut borrowed = data.borrow_mut();
    *borrowed += 1;
}

println!("{}", data.borrow());  // 6
```

---

## Testing

### Test Patterns

**Basic unit test:**
```rust
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 3), 5);
        assert_ne!(add(2, 3), 6);
    }

    #[test]
    fn test_add_negative() {
        assert_eq!(add(-2, -3), -5);
    }
}
```

**Testing errors:**
```rust
#[test]
fn test_error() {
    let result = divide(10, 0);
    assert!(result.is_err());
}

#[test]
#[should_panic(expected = "division by zero")]
fn test_panic() {
    divide_panic(10, 0);
}
```

**Test with setup:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    fn setup() -> Database {
        Database::new_test()
    }

    #[test]
    fn test_query() {
        let db = setup();
        let result = db.query("SELECT * FROM users");
        assert!(result.is_ok());
    }
}
```

**Async tests:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_async_function() {
        let result = fetch_data("https://api.example.com").await;
        assert!(result.is_ok());
    }
}
```

**Property-based testing with proptest:**
```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_add_commutative(a: i32, b: i32) {
        prop_assert_eq!(add(a, b), add(b, a));
    }
}
```

### Running Tests

**Run all tests:**
```bash
cargo test
```

**Run specific test:**
```bash
cargo test test_add
```

**Run tests with output:**
```bash
cargo test -- --nocapture
```

**Run tests in single thread:**
```bash
cargo test -- --test-threads=1
```

**Run ignored tests:**
```rust
#[test]
#[ignore]
fn expensive_test() {
    // long-running test
}
```

```bash
cargo test -- --ignored
```

**Integration tests:**
```
tests/
└── integration_test.rs
```

```rust
// tests/integration_test.rs
use my_crate;

#[test]
fn test_integration() {
    // test code
}
```

### Benchmarking

**Benchmark with Criterion:**
```rust
// benches/my_benchmark.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 1,
        1 => 1,
        n => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

fn criterion_benchmark(c: &mut Criterion) {
    c.bench_function("fib 20", |b| b.iter(|| fibonacci(black_box(20))));
}

criterion_group!(benches, criterion_benchmark);
criterion_main!(benches);
```

**Run benchmarks:**
```bash
cargo bench
```

**Add to `Cargo.toml`:**
```toml
[dev-dependencies]
criterion = "0.5"

[[bench]]
name = "my_benchmark"
harness = false
```

---

## Security

### Security Scanners

Auto Code integrates these security tools for Rust projects:

| Tool | Purpose | Usage |
|------|---------|-------|
| **cargo-audit** | Vulnerability scanner | `cargo audit` |
| **cargo-deny** | Dependency linter | `cargo deny check` |
| **cargo-geiger** | Unsafe code detector | `cargo geiger` |
| **clippy** | Linter and code quality | `cargo clippy` |

**Install security tools:**
```bash
# cargo-audit
cargo install cargo-audit

# cargo-deny
cargo install cargo-deny

# cargo-geiger
cargo install cargo-geiger

# clippy (included with rustup)
rustup component add clippy
```

### Common Vulnerabilities

**Dangerous patterns to avoid:**

- `unwrap()` - Can panic on None/Err
- `expect()` - Can panic with message
- `unsafe` blocks - Bypass safety checks
- `transmute` - Unsafe type conversion
- `panic!()` - Should use Result instead
- Unvalidated user input
- SQL injection via string concatenation
- Command injection via shell execution

### Best Practices

**✅ DO:**

1. **Use Result instead of unwrap:**
   ```rust
   // ✅ CORRECT
   fn read_config() -> Result<Config, std::io::Error> {
       let contents = std::fs::read_to_string("config.toml")?;
       parse_config(&contents)
   }

   // ❌ WRONG
   fn read_config() -> Config {
       let contents = std::fs::read_to_string("config.toml").unwrap();
       parse_config(&contents).unwrap()
   }
   ```

2. **Validate user input:**
   ```rust
   fn parse_user_id(input: &str) -> Result<u32, ParseError> {
       let id: u32 = input.parse()
           .map_err(|_| ParseError::InvalidFormat)?;

       if id == 0 {
           return Err(ParseError::ZeroNotAllowed);
       }

       Ok(id)
   }
   ```

3. **Use prepared statements for SQL:**
   ```rust
   // With SQLx
   let user = sqlx::query_as!(
       User,
       "SELECT * FROM users WHERE id = ?",
       user_id
   )
   .fetch_one(&pool)
   .await?;
   ```

4. **Avoid command injection:**
   ```rust
   use std::process::Command;

   // ✅ CORRECT - Separate arguments
   let output = Command::new("ls")
       .arg("-la")
       .arg(user_input)
       .output()?;

   // ❌ WRONG - Shell injection risk
   let output = Command::new("sh")
       .arg("-c")
       .arg(format!("ls -la {}", user_input))
       .output()?;
   ```

5. **Use secure random number generation:**
   ```rust
   use rand::Rng;
   use rand::rngs::OsRng;

   let mut rng = OsRng;
   let token: u64 = rng.gen();
   ```

**❌ DON'T:**

1. **Don't use unwrap in production code:**
   ```rust
   // ❌ WRONG
   let file = File::open("config.toml").unwrap();

   // ✅ CORRECT
   let file = File::open("config.toml")?;
   ```

2. **Don't ignore clippy warnings:**
   ```bash
   cargo clippy -- -D warnings
   ```

3. **Don't use unsafe without documentation:**
   ```rust
   // ❌ WRONG
   unsafe {
       // mysterious unsafe code
   }

   // ✅ CORRECT
   // SAFETY: This is safe because we guarantee that ptr is valid
   // and aligned, and the memory region is properly initialized.
   unsafe {
       *ptr = value;
   }
   ```

---

## Framework-Specific Patterns

### Actix-web

**Basic handler:**
```rust
use actix_web::{web, App, HttpResponse, HttpServer, Result};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct UserRequest {
    name: String,
    email: String,
}

#[derive(Serialize)]
struct UserResponse {
    id: u32,
    name: String,
}

async fn create_user(user: web::Json<UserRequest>) -> Result<HttpResponse> {
    let response = UserResponse {
        id: 1,
        name: user.name.clone(),
    };

    Ok(HttpResponse::Ok().json(response))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .route("/users", web::post().to(create_user))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
```

**Middleware:**
```rust
use actix_web::{dev::ServiceRequest, Error, HttpMessage};
use actix_web_httpauth::extractors::bearer::BearerAuth;

async fn validator(
    req: ServiceRequest,
    credentials: BearerAuth,
) -> Result<ServiceRequest, (Error, ServiceRequest)> {
    if validate_token(credentials.token()) {
        Ok(req)
    } else {
        Err((Error::from(AuthError), req))
    }
}
```

**State management:**
```rust
use actix_web::web::Data;
use std::sync::Mutex;

struct AppState {
    counter: Mutex<i32>,
}

async fn increment(data: Data<AppState>) -> HttpResponse {
    let mut counter = data.counter.lock().unwrap();
    *counter += 1;
    HttpResponse::Ok().json(*counter)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let state = Data::new(AppState {
        counter: Mutex::new(0),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .route("/increment", web::get().to(increment))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
```

### Rocket

**Basic handler:**
```rust
#[macro_use] extern crate rocket;

use rocket::serde::json::Json;
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct UserRequest {
    name: String,
    email: String,
}

#[derive(Serialize)]
struct UserResponse {
    id: u32,
    name: String,
}

#[post("/users", data = "<user>")]
fn create_user(user: Json<UserRequest>) -> Json<UserResponse> {
    Json(UserResponse {
        id: 1,
        name: user.name.clone(),
    })
}

#[launch]
fn rocket() -> _ {
    rocket::build()
        .mount("/api", routes![create_user])
}
```

**Request guards:**
```rust
use rocket::request::{FromRequest, Outcome, Request};

struct AuthUser {
    id: u32,
}

#[rocket::async_trait]
impl<'r> FromRequest<'r> for AuthUser {
    type Error = AuthError;

    async fn from_request(req: &'r Request<'_>) -> Outcome<Self, Self::Error> {
        match req.headers().get_one("Authorization") {
            Some(token) if validate_token(token) => {
                Outcome::Success(AuthUser { id: 1 })
            }
            _ => Outcome::Error((Status::Unauthorized, AuthError)),
        }
    }
}

#[get("/profile")]
fn profile(user: AuthUser) -> String {
    format!("User ID: {}", user.id)
}
```

### Axum

**Basic handler:**
```rust
use axum::{
    extract::Json,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct UserRequest {
    name: String,
    email: String,
}

#[derive(Serialize)]
struct UserResponse {
    id: u32,
    name: String,
}

async fn create_user(Json(user): Json<UserRequest>) -> Json<UserResponse> {
    Json(UserResponse {
        id: 1,
        name: user.name,
    })
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/users", post(create_user));

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080")
        .await
        .unwrap();

    axum::serve(listener, app).await.unwrap();
}
```

**Middleware:**
```rust
use axum::{
    middleware::{self, Next},
    response::Response,
    http::Request,
};

async fn auth_middleware<B>(
    req: Request<B>,
    next: Next<B>,
) -> Result<Response, StatusCode> {
    let auth_header = req.headers()
        .get("Authorization")
        .and_then(|h| h.to_str().ok());

    match auth_header {
        Some(token) if validate_token(token) => Ok(next.run(req).await),
        _ => Err(StatusCode::UNAUTHORIZED),
    }
}

let app = Router::new()
    .route("/protected", get(handler))
    .layer(middleware::from_fn(auth_middleware));
```

**State management:**
```rust
use axum::{extract::State, Router};
use std::sync::Arc;

#[derive(Clone)]
struct AppState {
    db: Arc<Database>,
}

async fn handler(State(state): State<AppState>) -> String {
    // Use state.db
    "OK".to_string()
}

#[tokio::main]
async fn main() {
    let state = AppState {
        db: Arc::new(Database::new()),
    };

    let app = Router::new()
        .route("/", get(handler))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080")
        .await
        .unwrap();

    axum::serve(listener, app).await.unwrap();
}
```

### Tokio

**Basic async runtime:**
```rust
use tokio;

#[tokio::main]
async fn main() {
    let result = fetch_data().await;
    println!("Result: {:?}", result);
}

async fn fetch_data() -> Result<String, reqwest::Error> {
    let response = reqwest::get("https://api.example.com/data").await?;
    response.text().await
}
```

**Spawning tasks:**
```rust
use tokio;

#[tokio::main]
async fn main() {
    let handle1 = tokio::spawn(async {
        // task 1
        42
    });

    let handle2 = tokio::spawn(async {
        // task 2
        84
    });

    let (result1, result2) = tokio::join!(handle1, handle2);
    println!("Results: {:?}, {:?}", result1, result2);
}
```

**Channels:**
```rust
use tokio::sync::mpsc;

#[tokio::main]
async fn main() {
    let (tx, mut rx) = mpsc::channel(32);

    tokio::spawn(async move {
        tx.send("message").await.unwrap();
    });

    while let Some(msg) = rx.recv().await {
        println!("Received: {}", msg);
    }
}
```

---

## Code Generation

Auto Code generates idiomatic Rust code based on your project context:

1. **Framework detection** - Automatically detects Actix-web, Rocket, Axum, Tokio from `Cargo.toml`
2. **Idiomatic patterns** - Follows Rust community best practices
3. **Error handling** - Proper Result and Option handling, no unwrap in production
4. **Ownership** - Correct borrowing, lifetimes, and ownership patterns
5. **Testing** - Unit tests, integration tests, and property-based tests
6. **Security** - Avoids dangerous patterns, uses secure defaults
7. **Async/await** - Proper async runtime integration

**Example spec:**
```markdown
# Feature: User Authentication API

Create a REST API for user authentication with JWT tokens.

## Requirements
- POST /auth/register - Register new user
- POST /auth/login - Login and receive JWT
- GET /auth/profile - Get user profile (authenticated)

## Tech Stack
- Framework: Axum
- Database: SQLx with PostgreSQL
- Authentication: JWT with jsonwebtoken
```

Auto Code will:
- Detect Axum framework from `Cargo.toml`
- Generate handlers using Axum patterns
- Use proper error handling with thiserror
- Include unit and integration tests
- Follow Rust security best practices
- Add middleware for JWT validation
- Use async/await with Tokio runtime

---

## Additional Resources

- [The Rust Book](https://doc.rust-lang.org/book/)
- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- [Async Book](https://rust-lang.github.io/async-book/)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- [Cargo Book](https://doc.rust-lang.org/cargo/)
- [cargo-audit](https://github.com/rustsec/rustsec)
- [clippy](https://github.com/rust-lang/rust-clippy)

---

**Need help?** Check the [Troubleshooting Guide](../guides/TROUBLESHOOTING.md) or open an issue on GitHub.
