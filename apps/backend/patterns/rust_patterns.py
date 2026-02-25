"""
Rust Language Patterns Module
==============================

Idiomatic Rust code patterns for code generation and analysis.
"""


# =============================================================================
# ERROR HANDLING PATTERNS
# =============================================================================

ERROR_HANDLING_PATTERNS = {
    "result_basic": """fn function() -> Result<T, Error> {
    let value = operation()?;
    Ok(value)
}""",
    "result_with_context": """use anyhow::{Context, Result};

fn function() -> Result<T> {
    let value = operation()
        .context("Failed to perform operation")?;
    Ok(value)
}""",
    "custom_error": """use std::fmt;

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

impl std::error::Error for AppError {}""",
    "thiserror_enum": """use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Invalid input: {0}")]
    InvalidInput(String),
    #[error("IO error")]
    Io(#[from] std::io::Error),
}""",
    "option_handling": """fn find_item(id: u32) -> Option<Item> {
    items.iter()
        .find(|item| item.id == id)
        .cloned()
}

// Usage
match find_item(42) {
    Some(item) => println!("Found: {:?}", item),
    None => println!("Not found"),
}

// Or with if let
if let Some(item) = find_item(42) {
    println!("Found: {:?}", item);
}""",
    "error_propagation": """fn outer() -> Result<(), Error> {
    let data = read_data()?;
    let processed = process_data(data)?;
    save_data(processed)?;
    Ok(())
}""",
}


# =============================================================================
# OWNERSHIP AND BORROWING PATTERNS
# =============================================================================

OWNERSHIP_PATTERNS = {
    "move_semantics": """fn consume(value: String) {
    // value is moved here
    println!("{}", value);
}

fn borrow(value: &String) {
    // value is borrowed immutably
    println!("{}", value);
}

fn borrow_mut(value: &mut String) {
    // value is borrowed mutably
    value.push_str(" modified");
}""",
    "clone_pattern": """#[derive(Clone, Debug)]
struct Data {
    value: String,
}

fn use_clone(data: &Data) -> Data {
    data.clone()
}""",
    "lifetime_annotation": """fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() {
        x
    } else {
        y
    }
}""",
    "lifetime_struct": """struct ImportantExcerpt<'a> {
    part: &'a str,
}

impl<'a> ImportantExcerpt<'a> {
    fn level(&self) -> i32 {
        3
    }
}""",
    "smart_pointers": """use std::rc::Rc;
use std::sync::Arc;
use std::cell::RefCell;

// Reference counted (single-threaded)
let data = Rc::new(vec![1, 2, 3]);
let data_clone = Rc::clone(&data);

// Atomic reference counted (multi-threaded)
let shared = Arc::new(vec![1, 2, 3]);
let shared_clone = Arc::clone(&shared);

// Interior mutability
let mutable = RefCell::new(5);
*mutable.borrow_mut() += 1;""",
}


# =============================================================================
# TRAIT PATTERNS
# =============================================================================

TRAIT_PATTERNS = {
    "basic_trait": """trait Drawable {
    fn draw(&self);
}

struct Circle {
    radius: f64,
}

impl Drawable for Circle {
    fn draw(&self) {
        println!("Drawing circle with radius {}", self.radius);
    }
}""",
    "trait_with_default": """trait Logger {
    fn log(&self, message: &str) {
        println!("[LOG] {}", message);
    }

    fn error(&self, message: &str) {
        eprintln!("[ERROR] {}", message);
    }
}""",
    "trait_bounds": """fn print_info<T: Display + Debug>(item: &T) {
    println!("{}", item);
    println!("{:?}", item);
}

fn compare<T: PartialOrd>(a: T, b: T) -> bool {
    a > b
}""",
    "where_clause": """fn complex_function<T, U>(t: &T, u: &U) -> i32
where
    T: Display + Clone,
    U: Clone + Debug,
{
    // implementation
    0
}""",
    "associated_types": """trait Container {
    type Item;

    fn get(&self, index: usize) -> Option<&Self::Item>;
    fn add(&mut self, item: Self::Item);
}

impl Container for Vec<String> {
    type Item = String;

    fn get(&self, index: usize) -> Option<&Self::Item> {
        self.get(index)
    }

    fn add(&mut self, item: Self::Item) {
        self.push(item);
    }
}""",
    "derive_macros": """#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct User {
    pub id: u64,
    pub name: String,
    pub email: String,
}

#[derive(Debug, Default)]
pub struct Config {
    pub host: String,
    pub port: u16,
}""",
}


# =============================================================================
# ASYNC/AWAIT PATTERNS
# =============================================================================

ASYNC_PATTERNS = {
    "basic_async": """async fn fetch_data(url: &str) -> Result<String, Error> {
    let response = reqwest::get(url).await?;
    let body = response.text().await?;
    Ok(body)
}""",
    "tokio_spawn": """use tokio::task;

#[tokio::main]
async fn main() {
    let handle = task::spawn(async {
        // async work
        42
    });

    let result = handle.await.unwrap();
}""",
    "async_trait": """use async_trait::async_trait;

#[async_trait]
trait DataFetcher {
    async fn fetch(&self, id: u64) -> Result<Data, Error>;
}

struct ApiClient;

#[async_trait]
impl DataFetcher for ApiClient {
    async fn fetch(&self, id: u64) -> Result<Data, Error> {
        // implementation
        Ok(Data::default())
    }
}""",
    "select_pattern": """use tokio::select;

async fn race_tasks() {
    let task1 = async { /* work */ };
    let task2 = async { /* work */ };

    select! {
        result = task1 => {
            println!("Task 1 completed first");
        }
        result = task2 => {
            println!("Task 2 completed first");
        }
    }
}""",
    "timeout_pattern": """use tokio::time::{timeout, Duration};

async fn with_timeout() -> Result<Data, Error> {
    match timeout(Duration::from_secs(5), fetch_data()).await {
        Ok(result) => result,
        Err(_) => Err(Error::Timeout),
    }
}""",
    "stream_processing": """use futures::stream::{self, StreamExt};

async fn process_stream() {
    let items = vec![1, 2, 3, 4, 5];
    let stream = stream::iter(items);

    stream
        .map(|x| x * 2)
        .filter(|x| *x > 5)
        .for_each(|x| async move {
            println!("{}", x);
        })
        .await;
}""",
}


# =============================================================================
# STRUCT AND ENUM PATTERNS
# =============================================================================

STRUCT_PATTERNS = {
    "basic_struct": """pub struct User {
    pub id: u64,
    pub name: String,
    created_at: i64,
}

impl User {
    pub fn new(id: u64, name: String) -> Self {
        Self {
            id,
            name,
            created_at: chrono::Utc::now().timestamp(),
        }
    }
}""",
    "builder_pattern": """pub struct Config {
    host: String,
    port: u16,
    timeout: u64,
}

pub struct ConfigBuilder {
    host: Option<String>,
    port: Option<u16>,
    timeout: Option<u64>,
}

impl ConfigBuilder {
    pub fn new() -> Self {
        Self {
            host: None,
            port: None,
            timeout: None,
        }
    }

    pub fn host(mut self, host: impl Into<String>) -> Self {
        self.host = Some(host.into());
        self
    }

    pub fn port(mut self, port: u16) -> Self {
        self.port = Some(port);
        self
    }

    pub fn timeout(mut self, timeout: u64) -> Self {
        self.timeout = Some(timeout);
        self
    }

    pub fn build(self) -> Result<Config, &'static str> {
        Ok(Config {
            host: self.host.ok_or("host is required")?,
            port: self.port.unwrap_or(8080),
            timeout: self.timeout.unwrap_or(30),
        })
    }
}""",
    "enum_variants": """pub enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(i32, i32, i32),
}

impl Message {
    pub fn process(&self) {
        match self {
            Message::Quit => println!("Quitting"),
            Message::Move { x, y } => println!("Moving to ({}, {})", x, y),
            Message::Write(text) => println!("Writing: {}", text),
            Message::ChangeColor(r, g, b) => println!("Color: ({}, {}, {})", r, g, b),
        }
    }
}""",
    "tuple_struct": """pub struct Point(pub f64, pub f64);

pub struct Color(pub u8, pub u8, pub u8);

impl Point {
    pub fn distance(&self) -> f64 {
        (self.0.powi(2) + self.1.powi(2)).sqrt()
    }
}""",
}


# =============================================================================
# TESTING PATTERNS
# =============================================================================

TESTING_PATTERNS = {
    "unit_test": """#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_function() {
        let result = function(input);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_error_case() {
        let result = function(bad_input);
        assert!(result.is_err());
    }
}""",
    "test_with_setup": """#[cfg(test)]
mod tests {
    use super::*;

    fn setup() -> TestState {
        TestState {
            data: vec![1, 2, 3],
        }
    }

    #[test]
    fn test_with_state() {
        let state = setup();
        assert_eq!(state.data.len(), 3);
    }
}""",
    "parameterized_test": """#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cases() {
        let cases = vec![
            (1, 2, 3),
            (5, 5, 10),
            (0, 0, 0),
        ];

        for (a, b, expected) in cases {
            assert_eq!(add(a, b), expected);
        }
    }
}""",
    "async_test": """#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_async_function() {
        let result = async_function().await;
        assert!(result.is_ok());
    }
}""",
    "benchmark": """#![feature(test)]
extern crate test;

#[cfg(test)]
mod benches {
    use super::*;
    use test::Bencher;

    #[bench]
    fn bench_function(b: &mut Bencher) {
        b.iter(|| {
            function()
        });
    }
}""",
    "mock_trait": """#[cfg(test)]
mod tests {
    use super::*;
    use mockall::*;

    #[automock]
    trait Database {
        fn get(&self, id: u64) -> Result<User, Error>;
    }

    #[test]
    fn test_with_mock() {
        let mut mock = MockDatabase::new();
        mock.expect_get()
            .with(eq(1))
            .times(1)
            .returning(|_| Ok(User::default()));

        let result = mock.get(1);
        assert!(result.is_ok());
    }
}""",
}


# =============================================================================
# MACRO PATTERNS
# =============================================================================

MACRO_PATTERNS = {
    "declarative_macro": """macro_rules! vec_of_strings {
    ($($x:expr),*) => {
        vec![$($x.to_string()),*]
    };
}

// Usage
let strings = vec_of_strings!["hello", "world"];""",
    "macro_with_repetition": """macro_rules! hash_map {
    ($($key:expr => $val:expr),* $(,)?) => {
        {
            let mut map = ::std::collections::HashMap::new();
            $(map.insert($key, $val);)*
            map
        }
    };
}

// Usage
let map = hash_map! {
    "key1" => 1,
    "key2" => 2,
};""",
}


# =============================================================================
# ITERATOR PATTERNS
# =============================================================================

ITERATOR_PATTERNS = {
    "basic_iteration": """let numbers = vec![1, 2, 3, 4, 5];

// Consume iterator
let sum: i32 = numbers.iter().sum();

// Transform
let doubled: Vec<i32> = numbers.iter()
    .map(|x| x * 2)
    .collect();

// Filter
let evens: Vec<&i32> = numbers.iter()
    .filter(|x| *x % 2 == 0)
    .collect();""",
    "chain_methods": """let result: Vec<String> = data.iter()
    .filter(|x| x.is_valid())
    .map(|x| x.transform())
    .filter_map(|x| x.ok())
    .collect();""",
    "custom_iterator": """struct Counter {
    count: u32,
}

impl Counter {
    fn new() -> Counter {
        Counter { count: 0 }
    }
}

impl Iterator for Counter {
    type Item = u32;

    fn next(&mut self) -> Option<Self::Item> {
        if self.count < 5 {
            self.count += 1;
            Some(self.count)
        } else {
            None
        }
    }
}""",
}


# =============================================================================
# FRAMEWORK-SPECIFIC PATTERNS (ACTIX-WEB)
# =============================================================================

ACTIX_PATTERNS = {
    "actix_handler": """use actix_web::{web, HttpResponse, Result};

async fn handler(
    path: web::Path<(u32,)>,
    data: web::Json<RequestData>,
) -> Result<HttpResponse> {
    let id = path.into_inner().0;

    Ok(HttpResponse::Ok().json(ResponseData {
        id,
        message: data.message.clone(),
    }))
}""",
    "actix_app": """use actix_web::{web, App, HttpServer};

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .route("/health", web::get().to(health_check))
            .service(
                web::scope("/api/v1")
                    .route("/users", web::get().to(get_users))
                    .route("/users", web::post().to(create_user))
            )
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}""",
    "actix_middleware": """use actix_web::{
    dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
    Error,
};
use futures::future::{ready, LocalBoxFuture, Ready};

pub struct Logger;

impl<S, B> Transform<S, ServiceRequest> for Logger
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error>,
    S::Future: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type InitError = ();
    type Transform = LoggerMiddleware<S>;
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(LoggerMiddleware { service }))
    }
}""",
    "actix_state": """use actix_web::{web, App, HttpServer};
use std::sync::Mutex;

struct AppState {
    counter: Mutex<i32>,
}

async fn handler(data: web::Data<AppState>) -> String {
    let mut counter = data.counter.lock().unwrap();
    *counter += 1;
    format!("Count: {}", counter)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let state = web::Data::new(AppState {
        counter: Mutex::new(0),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .route("/", web::get().to(handler))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}""",
}


# =============================================================================
# FRAMEWORK-SPECIFIC PATTERNS (ROCKET)
# =============================================================================

ROCKET_PATTERNS = {
    "rocket_handler": """use rocket::{State, serde::json::Json};

#[get("/users/<id>")]
async fn get_user(id: u64, db: &State<Database>) -> Json<User> {
    let user = db.find_user(id).await;
    Json(user)
}

#[post("/users", data = "<user>")]
async fn create_user(user: Json<UserInput>) -> Json<User> {
    let created = User::create(user.into_inner()).await;
    Json(created)
}""",
    "rocket_app": """#[macro_use] extern crate rocket;

#[launch]
fn rocket() -> _ {
    rocket::build()
        .mount("/", routes![index, health])
        .mount("/api/v1", routes![get_users, create_user])
}""",
    "rocket_state": """use rocket::State;

struct AppConfig {
    max_connections: usize,
}

#[get("/config")]
fn get_config(config: &State<AppConfig>) -> String {
    format!("Max connections: {}", config.max_connections)
}

#[launch]
fn rocket() -> _ {
    rocket::build()
        .manage(AppConfig { max_connections: 100 })
        .mount("/", routes![get_config])
}""",
}


# =============================================================================
# FRAMEWORK-SPECIFIC PATTERNS (AXUM)
# =============================================================================

AXUM_PATTERNS = {
    "axum_handler": """use axum::{
    extract::{Path, Json},
    http::StatusCode,
};

async fn get_user(
    Path(id): Path<u64>,
) -> Result<Json<User>, StatusCode> {
    match find_user(id).await {
        Some(user) => Ok(Json(user)),
        None => Err(StatusCode::NOT_FOUND),
    }
}

async fn create_user(
    Json(payload): Json<CreateUser>,
) -> Result<Json<User>, StatusCode> {
    let user = User::create(payload).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(user))
}""",
    "axum_app": """use axum::{
    routing::{get, post},
    Router,
};

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/users", get(get_users).post(create_user))
        .route("/users/:id", get(get_user));

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080")
        .await
        .unwrap();

    axum::serve(listener, app).await.unwrap();
}""",
    "axum_state": """use axum::{
    extract::State,
    routing::get,
    Router,
};
use std::sync::Arc;

#[derive(Clone)]
struct AppState {
    db: Arc<Database>,
}

async fn handler(State(state): State<AppState>) -> String {
    format!("DB connected: {}", state.db.is_connected())
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
}""",
    "axum_middleware": """use axum::{
    extract::Request,
    http::StatusCode,
    middleware::{self, Next},
    response::Response,
    routing::get,
    Router,
};

async fn auth_middleware(
    req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    // Check authentication
    if !is_authenticated(&req) {
        return Err(StatusCode::UNAUTHORIZED);
    }

    Ok(next.run(req).await)
}

let app = Router::new()
    .route("/protected", get(handler))
    .layer(middleware::from_fn(auth_middleware));""",
}


# =============================================================================
# COMBINED PATTERNS EXPORT
# =============================================================================

RUST_PATTERNS = {
    "error_handling": ERROR_HANDLING_PATTERNS,
    "ownership": OWNERSHIP_PATTERNS,
    "traits": TRAIT_PATTERNS,
    "async": ASYNC_PATTERNS,
    "structs": STRUCT_PATTERNS,
    "testing": TESTING_PATTERNS,
    "macros": MACRO_PATTERNS,
    "iterators": ITERATOR_PATTERNS,
    "frameworks": {
        "actix": ACTIX_PATTERNS,
        "rocket": ROCKET_PATTERNS,
        "axum": AXUM_PATTERNS,
    },
}


__all__ = ["RUST_PATTERNS"]
