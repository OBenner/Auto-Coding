"""
Go Language Patterns Module
============================

Idiomatic Go code patterns for code generation and analysis.
"""


# =============================================================================
# ERROR HANDLING PATTERNS
# =============================================================================

ERROR_HANDLING_PATTERNS = {
    "basic_error_check": """if err != nil {
    return err
}""",
    "error_wrap": """if err != nil {
    return fmt.Errorf("context: %w", err)
}""",
    "error_with_cleanup": """if err != nil {
    cleanup()
    return err
}""",
    "custom_error": """type AppError struct {
    Code    int
    Message string
    Err     error
}

func (e *AppError) Error() string {
    return fmt.Sprintf("%s (code: %d): %v", e.Message, e.Code, e.Err)
}

func (e *AppError) Unwrap() error {
    return e.Err
}""",
}


# =============================================================================
# CONCURRENCY PATTERNS
# =============================================================================

CONCURRENCY_PATTERNS = {
    "goroutine_basic": """go func() {
    // concurrent work
}()""",
    "channel_communication": """ch := make(chan Type)
go func() {
    ch <- value
}()
result := <-ch""",
    "buffered_channel": """ch := make(chan Type, bufferSize)""",
    "worker_pool": """func worker(id int, jobs <-chan Job, results chan<- Result) {
    for job := range jobs {
        results <- process(job)
    }
}

jobs := make(chan Job, numJobs)
results := make(chan Result, numJobs)

for w := 1; w <= numWorkers; w++ {
    go worker(w, jobs, results)
}

for j := 1; j <= numJobs; j++ {
    jobs <- Job{j}
}
close(jobs)

for r := 1; r <= numJobs; r++ {
    <-results
}""",
    "context_cancellation": """ctx, cancel := context.WithCancel(context.Background())
defer cancel()

go func(ctx context.Context) {
    select {
    case <-ctx.Done():
        return
    case <-time.After(timeout):
        // work
    }
}(ctx)""",
    "select_pattern": """select {
case msg := <-ch1:
    // handle ch1
case msg := <-ch2:
    // handle ch2
case <-time.After(timeout):
    // timeout
default:
    // non-blocking
}""",
    "mutex_protection": """var mu sync.Mutex
var data Type

mu.Lock()
defer mu.Unlock()
// critical section""",
    "rwmutex_pattern": """var mu sync.RWMutex
var data Type

// Read
mu.RLock()
defer mu.RUnlock()
// read data

// Write
mu.Lock()
defer mu.Unlock()
// modify data""",
    "waitgroup": """var wg sync.WaitGroup

for i := 0; i < n; i++ {
    wg.Add(1)
    go func(id int) {
        defer wg.Done()
        // work
    }(i)
}

wg.Wait()""",
}


# =============================================================================
# STRUCT AND INTERFACE PATTERNS
# =============================================================================

STRUCT_PATTERNS = {
    "constructor_pattern": """type Config struct {
    Host string
    Port int
}

func NewConfig(host string, port int) *Config {
    return &Config{
        Host: host,
        Port: port,
    }
}""",
    "functional_options": """type Option func(*Config)

func WithHost(host string) Option {
    return func(c *Config) {
        c.Host = host
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
}""",
    "interface_implementation": """type Reader interface {
    Read(p []byte) (n int, err error)
}

type MyReader struct {
    // fields
}

func (r *MyReader) Read(p []byte) (n int, err error) {
    // implementation
    return len(p), nil
}""",
    "embedding": """type Base struct {
    ID   int
    Name string
}

type Extended struct {
    Base
    Extra string
}""",
    "method_receiver": """func (s *Struct) PointerReceiver() {
    // can modify s
}

func (s Struct) ValueReceiver() {
    // cannot modify s
}""",
}


# =============================================================================
# HTTP AND WEB PATTERNS
# =============================================================================

HTTP_PATTERNS = {
    "http_handler": """func handler(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}""",
    "http_server": """server := &http.Server{
    Addr:         ":8080",
    Handler:      mux,
    ReadTimeout:  15 * time.Second,
    WriteTimeout: 15 * time.Second,
    IdleTimeout:  60 * time.Second,
}

if err := server.ListenAndServe(); err != nil {
    log.Fatal(err)
}""",
    "middleware": """func middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // before
        next.ServeHTTP(w, r)
        // after
    })
}""",
    "json_response": """type Response struct {
    Status  string      `json:"status"`
    Data    interface{} `json:"data,omitempty"`
    Error   string      `json:"error,omitempty"`
}

func sendJSON(w http.ResponseWriter, status int, data interface{}) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteStatus(status)
    json.NewEncoder(w).Encode(Response{
        Status: "success",
        Data:   data,
    })
}""",
}


# =============================================================================
# TESTING PATTERNS
# =============================================================================

TESTING_PATTERNS = {
    "basic_test": """func TestFunction(t *testing.T) {
    got := Function()
    want := expectedValue

    if got != want {
        t.Errorf("Function() = %v, want %v", got, want)
    }
}""",
    "table_driven_test": """func TestFunction(t *testing.T) {
    tests := []struct {
        name    string
        input   Type
        want    Type
        wantErr bool
    }{
        {"case1", input1, want1, false},
        {"case2", input2, want2, true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := Function(tt.input)
            if (err != nil) != tt.wantErr {
                t.Errorf("error = %v, wantErr %v", err, tt.wantErr)
                return
            }
            if got != tt.want {
                t.Errorf("got %v, want %v", got, tt.want)
            }
        })
    }
}""",
    "benchmark": """func BenchmarkFunction(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Function()
    }
}""",
    "test_helper": """func setup(t *testing.T) (*State, func()) {
    state := &State{}
    // setup

    cleanup := func() {
        // cleanup
    }

    return state, cleanup
}

func TestWithSetup(t *testing.T) {
    state, cleanup := setup(t)
    defer cleanup()

    // test using state
}""",
}


# =============================================================================
# PACKAGE AND MODULE PATTERNS
# =============================================================================

PACKAGE_PATTERNS = {
    "package_declaration": """package packagename

import (
    "fmt"
    "context"

    "github.com/user/package"
)""",
    "internal_package": """// Package internal provides implementation details
// not exposed in the public API
package internal""",
    "init_function": """func init() {
    // initialization code
    // runs once when package is imported
}""",
    "exported_unexported": """// Public is exported (starts with capital letter)
type Public struct {
    ExportedField   string
    unexportedField string
}

// private is unexported (starts with lowercase letter)
type private struct {
    field string
}""",
}


# =============================================================================
# FILE I/O AND RESOURCE PATTERNS
# =============================================================================

IO_PATTERNS = {
    "defer_close": """file, err := os.Open("file.txt")
if err != nil {
    return err
}
defer file.Close()

// use file""",
    "read_file": """data, err := os.ReadFile("file.txt")
if err != nil {
    return err
}""",
    "write_file": """err := os.WriteFile("file.txt", data, 0644)
if err != nil {
    return err
}""",
    "buffered_io": """file, err := os.Open("file.txt")
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
}""",
}


# =============================================================================
# FRAMEWORK-SPECIFIC PATTERNS
# =============================================================================

GIN_PATTERNS = {
    "gin_handler": """func handler(c *gin.Context) {
    var req RequestType
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    c.JSON(http.StatusOK, gin.H{"status": "success"})
}""",
    "gin_middleware": """func middleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // before request
        c.Next()
        // after request
    }
}""",
    "gin_router": """router := gin.Default()
router.Use(middleware())

v1 := router.Group("/api/v1")
{
    v1.GET("/users", getUsers)
    v1.POST("/users", createUser)
}

router.Run(":8080")""",
}

ECHO_PATTERNS = {
    "echo_handler": """func handler(c echo.Context) error {
    var req RequestType
    if err := c.Bind(&req); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{
            "error": err.Error(),
        })
    }

    return c.JSON(http.StatusOK, response)
}""",
    "echo_middleware": """func middleware(next echo.HandlerFunc) echo.HandlerFunc {
    return func(c echo.Context) error {
        // before
        err := next(c)
        // after
        return err
    }
}""",
}

FIBER_PATTERNS = {
    "fiber_handler": """func handler(c *fiber.Ctx) error {
    var req RequestType
    if err := c.BodyParser(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    return c.JSON(response)
}""",
    "fiber_middleware": """func middleware(c *fiber.Ctx) error {
    // before
    err := c.Next()
    // after
    return err
}""",
}


# =============================================================================
# COMBINED PATTERNS EXPORT
# =============================================================================

GO_PATTERNS = {
    "error_handling": ERROR_HANDLING_PATTERNS,
    "concurrency": CONCURRENCY_PATTERNS,
    "structs": STRUCT_PATTERNS,
    "http": HTTP_PATTERNS,
    "testing": TESTING_PATTERNS,
    "packages": PACKAGE_PATTERNS,
    "io": IO_PATTERNS,
    "frameworks": {
        "gin": GIN_PATTERNS,
        "echo": ECHO_PATTERNS,
        "fiber": FIBER_PATTERNS,
    },
}


__all__ = ["GO_PATTERNS"]
