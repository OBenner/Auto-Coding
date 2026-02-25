# Go Language Support

Auto Code provides first-class support for Go development with idiomatic code generation, framework detection, security scanning, and testing integration.

## Table of Contents

- [Setup](#setup)
  - [Go Installation](#go-installation)
  - [Project Setup](#project-setup)
  - [Module Management](#module-management)
- [Supported Frameworks](#supported-frameworks)
- [Idiomatic Patterns](#idiomatic-patterns)
  - [Error Handling](#error-handling)
  - [Concurrency](#concurrency)
  - [Structs and Interfaces](#structs-and-interfaces)
  - [HTTP and Web](#http-and-web)
  - [File I/O](#file-io)
  - [Package Organization](#package-organization)
- [Testing](#testing)
  - [Test Patterns](#test-patterns)
  - [Running Tests](#running-tests)
  - [Benchmarking](#benchmarking)
- [Security](#security)
  - [Security Scanners](#security-scanners)
  - [Common Vulnerabilities](#common-vulnerabilities)
  - [Best Practices](#best-practices)
- [Framework-Specific Patterns](#framework-specific-patterns)
  - [Gin](#gin)
  - [Echo](#echo)
  - [Fiber](#fiber)
- [Code Generation](#code-generation)

---

## Setup

### Go Installation

Install Go 1.21 or later:

**macOS:**
```bash
brew install go
```

**Linux:**
```bash
# Download and install
wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz

# Add to PATH
export PATH=$PATH:/usr/local/go/bin
```

**Windows:**
Download the installer from [go.dev/dl](https://go.dev/dl/) and follow the installation wizard.

**Verify installation:**
```bash
go version
```

### Project Setup

Create a new Go project:

```bash
# Create project directory
mkdir my-go-project
cd my-go-project

# Initialize Go module
go mod init github.com/username/my-go-project

# Create main.go
cat > main.go << 'EOF'
package main

import "fmt"

func main() {
    fmt.Println("Hello, Auto Code!")
}
EOF

# Run the project
go run main.go
```

### Module Management

**Add dependencies:**
```bash
go get github.com/gin-gonic/gin@latest
```

**Update dependencies:**
```bash
go get -u ./...
go mod tidy
```

**Vendor dependencies:**
```bash
go mod vendor
```

---

## Supported Frameworks

Auto Code automatically detects and provides idiomatic patterns for these Go web frameworks:

| Framework | Detection | Use Case |
|-----------|-----------|----------|
| **Gin** | `go.mod` contains `github.com/gin-gonic/gin` | High-performance HTTP web framework |
| **Echo** | `go.mod` contains `github.com/labstack/echo` | Minimalist web framework |
| **Fiber** | `go.mod` contains `github.com/gofiber/fiber` | Express-inspired web framework |
| **Chi** | `go.mod` contains `github.com/go-chi/chi` | Lightweight router |
| **Gorilla** | `go.mod` contains `github.com/gorilla/mux` | Powerful HTTP router |
| **Beego** | `go.mod` contains `github.com/beego/beego` | Full-featured MVC framework |
| **Revel** | `go.mod` contains `github.com/revel/revel` | High-productivity web framework |

---

## Idiomatic Patterns

Auto Code generates idiomatic Go code following community best practices.

### Error Handling

**Basic error checking:**
```go
file, err := os.Open("file.txt")
if err != nil {
    return err
}
defer file.Close()
```

**Error wrapping (Go 1.13+):**
```go
if err != nil {
    return fmt.Errorf("failed to open file: %w", err)
}
```

**Custom errors:**
```go
type AppError struct {
    Code    int
    Message string
    Err     error
}

func (e *AppError) Error() string {
    return fmt.Sprintf("%s (code: %d): %v", e.Message, e.Code, e.Err)
}

func (e *AppError) Unwrap() error {
    return e.Err
}
```

### Concurrency

**Goroutines:**
```go
go func() {
    // concurrent work
}()
```

**Channels:**
```go
ch := make(chan string)
go func() {
    ch <- "message"
}()
message := <-ch
```

**Worker pool pattern:**
```go
func worker(id int, jobs <-chan Job, results chan<- Result) {
    for job := range jobs {
        results <- process(job)
    }
}

jobs := make(chan Job, 100)
results := make(chan Result, 100)

for w := 1; w <= 5; w++ {
    go worker(w, jobs, results)
}

for j := 1; j <= 100; j++ {
    jobs <- Job{j}
}
close(jobs)

for r := 1; r <= 100; r++ {
    <-results
}
```

**Context for cancellation:**
```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

go func(ctx context.Context) {
    select {
    case <-ctx.Done():
        return
    case <-time.After(1 * time.Second):
        // work
    }
}(ctx)
```

**Sync primitives:**
```go
// Mutex
var mu sync.Mutex
mu.Lock()
defer mu.Unlock()
// critical section

// RWMutex (multiple readers, single writer)
var rwmu sync.RWMutex
rwmu.RLock()
defer rwmu.RUnlock()
// read data

// WaitGroup
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    wg.Add(1)
    go func(id int) {
        defer wg.Done()
        // work
    }(i)
}
wg.Wait()
```

### Structs and Interfaces

**Constructor pattern:**
```go
type Config struct {
    Host string
    Port int
}

func NewConfig(host string, port int) *Config {
    return &Config{
        Host: host,
        Port: port,
    }
}
```

**Functional options pattern:**
```go
type Option func(*Config)

func WithHost(host string) Option {
    return func(c *Config) {
        c.Host = host
    }
}

func WithPort(port int) Option {
    return func(c *Config) {
        c.Port = port
    }
}

func NewConfig(opts ...Option) *Config {
    c := &Config{
        Host: "localhost",
        Port: 8080,
    }
    for _, opt := range opts {
        opt(c)
    }
    return c
}

// Usage
cfg := NewConfig(WithHost("0.0.0.0"), WithPort(3000))
```

**Interface implementation:**
```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type MyReader struct {
    // fields
}

func (r *MyReader) Read(p []byte) (n int, err error) {
    // implementation
    return len(p), nil
}
```

**Struct embedding:**
```go
type Base struct {
    ID   int
    Name string
}

type Extended struct {
    Base
    Extra string
}

// Usage
e := Extended{
    Base: Base{ID: 1, Name: "test"},
    Extra: "additional data",
}
fmt.Println(e.ID)  // Access embedded field directly
```

### HTTP and Web

**HTTP handler:**
```go
func handler(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}
```

**HTTP server with timeouts:**
```go
server := &http.Server{
    Addr:         ":8080",
    Handler:      mux,
    ReadTimeout:  15 * time.Second,
    WriteTimeout: 15 * time.Second,
    IdleTimeout:  60 * time.Second,
}

if err := server.ListenAndServe(); err != nil {
    log.Fatal(err)
}
```

**Middleware pattern:**
```go
func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        log.Printf("%s %s", r.Method, r.URL.Path)
        next.ServeHTTP(w, r)
    })
}

// Usage
mux := http.NewServeMux()
mux.HandleFunc("/", handler)
if err := http.ListenAndServe(":8080", loggingMiddleware(mux)); err != nil {
    log.Fatalf("server error: %v", err)
}
```

**JSON response helper:**
```go
type Response struct {
    Status string      `json:"status"`
    Data   interface{} `json:"data,omitempty"`
    Error  string      `json:"error,omitempty"`
}

func sendJSON(w http.ResponseWriter, status int, data interface{}) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(Response{
        Status: "success",
        Data:   data,
    })
}
```

### File I/O

**Read file:**
```go
data, err := os.ReadFile("file.txt")
if err != nil {
    return err
}
```

**Write file:**
```go
err := os.WriteFile("file.txt", data, 0644)
if err != nil {
    return err
}
```

**Buffered I/O:**
```go
file, err := os.Open("large-file.txt")
if err != nil {
    return err
}
defer file.Close()

scanner := bufio.NewScanner(file)
for scanner.Scan() {
    line := scanner.Text()
    // process line
}

if err := scanner.Err(); err != nil {
    return err
}
```

### Package Organization

**Package structure:**
```
my-project/
├── cmd/
│   └── myapp/
│       └── main.go        # Application entrypoint
├── internal/
│   ├── handlers/          # HTTP handlers
│   ├── models/            # Data models
│   └── services/          # Business logic
├── pkg/
│   └── utils/             # Public utilities
├── go.mod
└── go.sum
```

**Package declaration:**
```go
package mypackage

import (
    "context"
    "fmt"

    "github.com/external/package"
)
```

**Exported vs unexported:**
```go
// Public is exported (starts with capital letter)
type Public struct {
    ExportedField   string
    unexportedField string
}

// private is unexported (starts with lowercase letter)
type private struct {
    field string
}
```

---

## Testing

### Test Patterns

**Basic test:**
```go
func TestAdd(t *testing.T) {
    got := Add(2, 3)
    want := 5

    if got != want {
        t.Errorf("Add(2, 3) = %d, want %d", got, want)
    }
}
```

**Table-driven tests (recommended):**
```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name string
        a    int
        b    int
        want int
    }{
        {"positive numbers", 2, 3, 5},
        {"negative numbers", -2, -3, -5},
        {"zero", 0, 0, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.want {
                t.Errorf("Add(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.want)
            }
        })
    }
}
```

**Test setup and cleanup:**
```go
func TestWithSetup(t *testing.T) {
    // Setup
    db := setupTestDB(t)
    defer db.Close()

    // Test
    result := queryDB(db)
    if result == nil {
        t.Fatal("Expected result, got nil")
    }
}

func setupTestDB(t *testing.T) *DB {
    t.Helper()
    db, err := OpenDB("test.db")
    if err != nil {
        t.Fatalf("Failed to open test DB: %v", err)
    }
    return db
}
```

### Running Tests

**Run all tests:**
```bash
go test ./...
```

**Run tests with coverage:**
```bash
go test -cover ./...
```

**Generate coverage report:**
```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

**Run specific test:**
```bash
go test -run TestAdd
```

**Verbose output:**
```bash
go test -v ./...
```

**Run tests in parallel:**
```go
func TestParallel(t *testing.T) {
    t.Parallel()
    // test code
}
```

### Benchmarking

**Benchmark function:**
```go
func BenchmarkAdd(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Add(2, 3)
    }
}
```

**Run benchmarks:**
```bash
go test -bench=.
```

**Benchmark with memory stats:**
```bash
go test -bench=. -benchmem
```

---

## Security

### Security Scanners

Auto Code integrates these security tools for Go projects:

| Tool | Purpose | Usage |
|------|---------|-------|
| **gosec** | Security scanner | `gosec ./...` |
| **staticcheck** | Static analysis | `staticcheck ./...` |
| **govulncheck** | Vulnerability scanner | `govulncheck ./...` |

**Install security tools:**
```bash
# gosec
go install github.com/securego/gosec/v2/cmd/gosec@latest

# staticcheck
go install honnef.co/go/tools/cmd/staticcheck@latest

# govulncheck
go install golang.org/x/vuln/cmd/govulncheck@latest
```

### Common Vulnerabilities

**Dangerous functions to avoid:**

- `exec.Command` - Command injection risk
- `syscall.Exec` - Command injection risk
- `template.HTML` - XSS risk if not sanitized
- `sql.Query` - SQL injection risk without parameterization
- `http.Get` - SSRF risk without URL validation
- `crypto/md5` - Weak hash algorithm
- `crypto/sha1` - Weak hash algorithm
- `math/rand` - Not cryptographically secure
- `unsafe.Pointer` - Memory safety issues

### Best Practices

**✅ DO:**

1. **Use prepared statements for SQL:**
   ```go
   stmt, err := db.Prepare("SELECT * FROM users WHERE id = ?")
   if err != nil {
       return err
   }
   defer stmt.Close()

   rows, err := stmt.Query(userID)
   ```

2. **Use crypto/rand for random values:**
   ```go
   import "crypto/rand"

   b := make([]byte, 32)
   _, err := rand.Read(b)
   ```

3. **Use strong hash algorithms:**
   ```go
   import "crypto/sha256"

   hash := sha256.Sum256(data)
   ```

4. **Validate and sanitize user input:**
   ```go
   func sanitizeInput(input string) string {
       // Trim whitespace and reject inputs with dangerous characters
       input = strings.TrimSpace(input)
       if strings.ContainsAny(input, "<>\"';&|`") {
           return ""
       }
       return input
   }
   ```

5. **Use context for timeouts:**
   ```go
   ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
   defer cancel()

   req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
   ```

**❌ DON'T:**

1. **Don't use string concatenation for SQL:**
   ```go
   // ❌ WRONG - SQL injection risk
   query := "SELECT * FROM users WHERE name = '" + username + "'"

   // ✅ CORRECT - Use prepared statements
   stmt, err := db.Prepare("SELECT * FROM users WHERE name = ?")
   ```

2. **Don't use math/rand for secrets:**
   ```go
   // ❌ WRONG - Predictable randomness
   token := rand.Intn(1000000)

   // ✅ CORRECT - Cryptographically secure
   b := make([]byte, 32)
   _, err := rand.Read(b) // import "crypto/rand"
   ```

3. **Don't ignore errors:**
   ```go
   // ❌ WRONG
   file, _ := os.Open("file.txt")

   // ✅ CORRECT
   file, err := os.Open("file.txt")
   if err != nil {
       return err
   }
   defer file.Close()
   ```

---

## Framework-Specific Patterns

### Gin

**Basic handler:**
```go
func handler(c *gin.Context) {
    var req RequestType
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    c.JSON(http.StatusOK, gin.H{"status": "success"})
}
```

**Middleware:**
```go
func authMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        token := c.GetHeader("Authorization")
        if token == "" {
            c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
                "error": "unauthorized",
            })
            return
        }
        c.Next()
    }
}
```

**Router setup:**
```go
router := gin.Default()
router.Use(authMiddleware())

v1 := router.Group("/api/v1")
{
    v1.GET("/users", getUsers)
    v1.POST("/users", createUser)
    v1.GET("/users/:id", getUser)
    v1.PUT("/users/:id", updateUser)
    v1.DELETE("/users/:id", deleteUser)
}

router.Run(":8080")
```

### Echo

**Handler:**
```go
func handler(c echo.Context) error {
    var req RequestType
    if err := c.Bind(&req); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{
            "error": err.Error(),
        })
    }

    return c.JSON(http.StatusOK, response)
}
```

**Middleware:**
```go
func authMiddleware(next echo.HandlerFunc) echo.HandlerFunc {
    return func(c echo.Context) error {
        token := c.Request().Header.Get("Authorization")
        if token == "" {
            return c.JSON(http.StatusUnauthorized, map[string]string{
                "error": "unauthorized",
            })
        }
        return next(c)
    }
}
```

### Fiber

**Handler:**
```go
func handler(c *fiber.Ctx) error {
    var req RequestType
    if err := c.BodyParser(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    return c.JSON(response)
}
```

**Middleware:**
```go
func authMiddleware(c *fiber.Ctx) error {
    token := c.Get("Authorization")
    if token == "" {
        return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
            "error": "unauthorized",
        })
    }
    return c.Next()
}
```

---

## Code Generation

Auto Code generates idiomatic Go code based on your project context:

1. **Framework detection** - Automatically detects Gin, Echo, Fiber, etc. from `go.mod`
2. **Idiomatic patterns** - Follows Go community best practices
3. **Error handling** - Proper error wrapping and checking
4. **Concurrency** - Safe goroutine and channel usage
5. **Testing** - Table-driven tests with proper setup/cleanup
6. **Security** - Avoids dangerous functions and patterns

**Example spec:**
```markdown
# Feature: User Authentication API

Create a REST API for user authentication with JWT tokens.

## Requirements
- POST /auth/register - Register new user
- POST /auth/login - Login and receive JWT
- GET /auth/profile - Get user profile (authenticated)

## Tech Stack
- Framework: Gin
- Database: PostgreSQL with pgx
- Authentication: JWT with golang-jwt/jwt
```

Auto Code will:
- Detect Gin framework from `go.mod`
- Generate handlers using Gin patterns
- Use proper error handling with error wrapping
- Include table-driven tests
- Follow Go security best practices
- Add middleware for JWT validation

---

## Additional Resources

- [Go Official Documentation](https://go.dev/doc/)
- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Go Security Best Practices](https://github.com/OWASP/Go-SCP)
- [gosec Security Scanner](https://github.com/securego/gosec)

---

**Need help?** Check the [Troubleshooting Guide](../../guides/TROUBLESHOOTING.md) or open an issue on GitHub.
