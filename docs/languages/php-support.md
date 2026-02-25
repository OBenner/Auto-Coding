# PHP Language Support

Auto Code provides first-class support for PHP development with idiomatic code generation, framework detection, security scanning, and testing integration.

## Table of Contents

- [Setup](#setup)
  - [PHP Installation](#php-installation)
  - [Project Setup](#project-setup)
  - [Dependency Management](#dependency-management)
- [Supported Frameworks](#supported-frameworks)
- [Idiomatic Patterns](#idiomatic-patterns)
  - [Type Declarations](#type-declarations)
  - [Error Handling](#error-handling)
  - [Classes and Objects](#classes-and-objects)
  - [Namespaces and Autoloading](#namespaces-and-autoloading)
  - [Traits](#traits)
  - [Arrays and Collections](#arrays-and-collections)
  - [Modern PHP Features](#modern-php-features)
- [Testing](#testing)
  - [Test Patterns](#test-patterns)
  - [Running Tests](#running-tests)
  - [Code Coverage](#code-coverage)
- [Security](#security)
  - [Security Scanners](#security-scanners)
  - [Common Vulnerabilities](#common-vulnerabilities)
  - [Best Practices](#best-practices)
- [Framework-Specific Patterns](#framework-specific-patterns)
  - [Laravel](#laravel)
  - [Symfony](#symfony)
  - [CodeIgniter](#codeigniter)
  - [Slim](#slim)
- [Code Generation](#code-generation)

---

## Setup

### PHP Installation

Install PHP 8.1 or later:

**macOS:**
```bash
brew install php
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install php php-cli php-mbstring php-xml php-curl php-zip
```

**Linux (CentOS/RHEL):**
```bash
sudo yum install php php-cli php-mbstring php-xml php-curl php-zip
```

**Windows:**
Download PHP from [windows.php.net](https://windows.php.net/download/) or use Chocolatey:
```bash
choco install php
```

**Verify installation:**
```bash
php --version
```

### Project Setup

Create a new PHP project:

```bash
# Create project directory
mkdir my-php-project
cd my-php-project

# Initialize composer
composer init

# Create index.php
cat > index.php << 'EOF'
<?php

declare(strict_types=1);

echo "Hello, Auto Code!\n";
EOF

# Run the project
php index.php
```

**Project structure (typical):**
```
my-php-project/
├── composer.json       # Dependency manifest
├── composer.lock       # Dependency lock file
├── src/                # Source files
│   └── index.php
├── tests/              # Test files
│   └── ExampleTest.php
├── vendor/             # Composer dependencies
└── .gitignore
```

### Dependency Management

**Composer** is the standard dependency manager for PHP.

**Install Composer:**
```bash
# macOS/Linux
curl -sS https://getcomposer.org/installer | php
sudo mv composer.phar /usr/local/bin/composer

# Or via Homebrew
brew install composer

# Windows
# Download from https://getcomposer.org/download/
```

**Add dependencies:**
```bash
composer require vendor/package
composer require --dev phpunit/phpunit
```

**Update dependencies:**
```bash
composer update
```

**Autoload configuration in `composer.json`:**
```json
{
    "autoload": {
        "psr-4": {
            "App\\": "src/"
        }
    },
    "autoload-dev": {
        "psr-4": {
            "Tests\\": "tests/"
        }
    }
}
```

**Generate autoloader:**
```bash
composer dump-autoload
```

---

## Supported Frameworks

Auto Code detects PHP frameworks and provides idiomatic patterns. Frameworks marked **Auto-detected** are identified automatically; others are recognized when specified.

| Framework | Detection | Auto-detected | Use Case |
|-----------|-----------|:---:|----------|
| **Laravel** | `composer.json` contains `laravel/framework` | ✅ | Full-stack web application framework |
| **Symfony** | `composer.json` contains `symfony/symfony` | ✅ | Enterprise web framework |
| **CodeIgniter** | `composer.json` contains `codeigniter4/framework` | ✅ | Lightweight MVC framework |
| **Slim** | `composer.json` contains `slim/slim` | — | Micro-framework for APIs |
| **Lumen** | `composer.json` contains `laravel/lumen-framework` | — | Laravel micro-framework |
| **Yii** | `composer.json` contains `yiisoft/yii2` | — | High-performance framework |
| **CakePHP** | `composer.json` contains `cakephp/cakephp` | — | Rapid development framework |
| **Phalcon** | `composer.json` contains `phalcon/cphalcon` | — | High-performance C-extension framework |
| **Laminas** | `composer.json` contains `laminas/laminas-mvc` | — | Enterprise components (formerly Zend) |

---

## Idiomatic Patterns

Auto Code generates idiomatic PHP code following modern PHP best practices (PHP 8.1+).

### Type Declarations

**Scalar type hints:**
```php
<?php

declare(strict_types=1);

function add(int $a, int $b): int
{
    return $a + $b;
}

function greet(string $name): string
{
    return "Hello, {$name}!";
}

function isValid(bool $check): bool
{
    return $check;
}
```

**Nullable types:**
```php
<?php

function findUser(int $id): ?User
{
    // Return User or null
    return $user ?? null;
}

function process(?string $input): void
{
    if ($input === null) {
        return;
    }
    // Process input
}
```

**Union types (PHP 8.0+):**
```php
<?php

function process(int|float $number): int|float
{
    return $number * 2;
}

function getId(): int|string
{
    return rand(0, 1) ? 123 : 'uuid-123';
}
```

**Mixed type:**
```php
<?php

function process(mixed $value): mixed
{
    return $value;
}
```

### Error Handling

**Exceptions:**
```php
<?php

class UserNotFoundException extends Exception {}

function findUser(int $id): User
{
    $user = $this->repository->find($id);

    if ($user === null) {
        throw new UserNotFoundException("User with ID {$id} not found");
    }

    return $user;
}

// Usage
try {
    $user = findUser(123);
} catch (UserNotFoundException $e) {
    echo "Error: " . $e->getMessage();
}
```

**Custom exception hierarchy:**
```php
<?php

abstract class AppException extends Exception
{
    public function getContext(): array
    {
        return [];
    }
}

class ValidationException extends AppException
{
    public function __construct(
        private array $errors,
        string $message = 'Validation failed'
    ) {
        parent::__construct($message);
    }

    public function getContext(): array
    {
        return ['errors' => $this->errors];
    }
}

class NotFoundException extends AppException {}
class UnauthorizedException extends AppException {}
```

**Try-catch with finally:**
```php
<?php

function processFile(string $path): void
{
    $handle = fopen($path, 'r');

    try {
        // Process file
        $content = fread($handle, filesize($path));
        // Do something with content
    } catch (Exception $e) {
        throw new ProcessingException("Failed to process file", 0, $e);
    } finally {
        fclose($handle);
    }
}
```

### Classes and Objects

**Constructor property promotion (PHP 8.0+):**
```php
<?php

class User
{
    public function __construct(
        private int $id,
        private string $name,
        private string $email,
        private readonly \DateTimeImmutable $createdAt
    ) {}

    public function getId(): int
    {
        return $this->id;
    }

    public function getName(): string
    {
        return $this->name;
    }
}

// Usage
$user = new User(1, 'John', 'john@example.com', new \DateTimeImmutable());
```

**Readonly properties (PHP 8.1+):**
```php
<?php

class Configuration
{
    public function __construct(
        public readonly string $apiUrl,
        public readonly string $apiKey,
        public readonly int $timeout
    ) {}
}

$config = new Configuration('https://api.example.com', 'key123', 30);
// $config->apiUrl = 'new-url'; // Error: Cannot modify readonly property
```

**Named arguments (PHP 8.0+):**
```php
<?php

function createUser(
    string $name,
    string $email,
    bool $isActive = true,
    ?string $role = null
): User {
    return new User($name, $email, $isActive, $role);
}

// Usage
$user = createUser(
    name: 'John Doe',
    email: 'john@example.com',
    role: 'admin'
);
```

**Static factory methods:**
```php
<?php

class User
{
    private function __construct(
        private string $name,
        private string $email
    ) {}

    public static function create(string $name, string $email): self
    {
        return new self($name, $email);
    }

    public static function fromArray(array $data): self
    {
        return new self($data['name'], $data['email']);
    }
}

// Usage
$user = User::create('John', 'john@example.com');
$user2 = User::fromArray(['name' => 'Jane', 'email' => 'jane@example.com']);
```

### Namespaces and Autoloading

**Namespace declaration:**
```php
<?php

declare(strict_types=1);

namespace App\Services;

use App\Models\User;
use App\Repositories\UserRepository;
use Psr\Log\LoggerInterface;

class UserService
{
    public function __construct(
        private UserRepository $repository,
        private LoggerInterface $logger
    ) {}

    public function findUser(int $id): ?User
    {
        return $this->repository->find($id);
    }
}
```

**Grouped use statements:**
```php
<?php

namespace App\Http\Controllers;

use App\Models\{User, Post, Comment};
use App\Services\{UserService, PostService};
use Illuminate\Http\{Request, Response};
```

**PSR-4 autoloading structure:**
```
src/
├── Controllers/
│   └── UserController.php      # App\Controllers\UserController
├── Models/
│   └── User.php                # App\Models\User
├── Services/
│   └── UserService.php         # App\Services\UserService
└── Repositories/
    └── UserRepository.php      # App\Repositories\UserRepository
```

### Traits

**Basic trait:**
```php
<?php

trait Timestampable
{
    private \DateTimeImmutable $createdAt;
    private \DateTimeImmutable $updatedAt;

    public function setCreatedAt(\DateTimeImmutable $date): void
    {
        $this->createdAt = $date;
    }

    public function getCreatedAt(): \DateTimeImmutable
    {
        return $this->createdAt;
    }
}

class User
{
    use Timestampable;

    public function __construct(
        private string $name,
        private string $email
    ) {
        $this->setCreatedAt(new \DateTimeImmutable());
    }
}
```

**Multiple traits:**
```php
<?php

trait Loggable
{
    protected function log(string $message): void
    {
        error_log($message);
    }
}

trait Cacheable
{
    protected function cache(string $key, mixed $value): void
    {
        // Cache implementation
    }
}

class Service
{
    use Loggable, Cacheable;

    public function process(): void
    {
        $this->log('Processing...');
        $this->cache('result', ['status' => 'done']);
    }
}
```

### Arrays and Collections

**Array functions:**
```php
<?php

$numbers = [1, 2, 3, 4, 5];

// Map
$doubled = array_map(fn($n) => $n * 2, $numbers);

// Filter
$evens = array_filter($numbers, fn($n) => $n % 2 === 0);

// Reduce
$sum = array_reduce($numbers, fn($carry, $n) => $carry + $n, 0);

// Find
$found = array_filter($users, fn($u) => $u->id === 123);
$user = reset($found) ?: null;
```

**Spread operator:**
```php
<?php

$array1 = [1, 2, 3];
$array2 = [4, 5, 6];
$merged = [...$array1, ...$array2];  // [1, 2, 3, 4, 5, 6]

function sum(int ...$numbers): int
{
    return array_sum($numbers);
}

sum(1, 2, 3, 4, 5);  // 15
```

**Array unpacking:**
```php
<?php

[$first, $second, ...$rest] = [1, 2, 3, 4, 5];
// $first = 1, $second = 2, $rest = [3, 4, 5]

['name' => $name, 'email' => $email] = $user;
```

### Modern PHP Features

**Enums (PHP 8.1+):**
```php
<?php

enum Status: string
{
    case PENDING = 'pending';
    case ACTIVE = 'active';
    case INACTIVE = 'inactive';

    public function label(): string
    {
        return match($this) {
            self::PENDING => 'Pending Approval',
            self::ACTIVE => 'Active',
            self::INACTIVE => 'Inactive',
        };
    }
}

// Usage
$status = Status::ACTIVE;
echo $status->value;  // 'active'
echo $status->label();  // 'Active'
```

**Match expression (PHP 8.0+):**
```php
<?php

$result = match($status) {
    'pending' => 'Waiting for approval',
    'active' => 'Currently active',
    'inactive' => 'Not active',
    default => 'Unknown status'
};

// With conditions
$message = match(true) {
    $age < 18 => 'Minor',
    $age >= 18 && $age < 65 => 'Adult',
    $age >= 65 => 'Senior',
};
```

**Nullsafe operator (PHP 8.0+):**
```php
<?php

// Old way
$country = null;
if ($user !== null && $user->getAddress() !== null) {
    $country = $user->getAddress()->getCountry();
}

// New way
$country = $user?->getAddress()?->getCountry();
```

**Attributes (PHP 8.0+):**
```php
<?php

#[Attribute]
class Route
{
    public function __construct(
        public string $path,
        public string $method = 'GET'
    ) {}
}

#[Route('/users', method: 'GET')]
class UserController
{
    #[Route('/users/{id}', method: 'GET')]
    public function show(int $id): User
    {
        // Implementation
    }
}
```

**First-class callable syntax (PHP 8.1+):**
```php
<?php

class Utils
{
    public static function double(int $n): int
    {
        return $n * 2;
    }
}

// Old way
$fn = ['Utils', 'double'];

// New way
$fn = Utils::double(...);

$numbers = [1, 2, 3];
$doubled = array_map(Utils::double(...), $numbers);
```

---

## Testing

### Test Patterns

**Basic PHPUnit test:**
```php
<?php

declare(strict_types=1);

namespace Tests\Unit;

use PHPUnit\Framework\TestCase;
use App\Services\Calculator;

class CalculatorTest extends TestCase
{
    public function test_add_two_numbers(): void
    {
        $calculator = new Calculator();
        $result = $calculator->add(2, 3);

        $this->assertEquals(5, $result);
    }

    public function test_divide_by_zero_throws_exception(): void
    {
        $this->expectException(\DivisionByZeroError::class);

        $calculator = new Calculator();
        $calculator->divide(10, 0);
    }
}
```

**Data providers:**
```php
<?php

class MathTest extends TestCase
{
    /**
     * @dataProvider additionProvider
     */
    public function test_addition(int $a, int $b, int $expected): void
    {
        $this->assertEquals($expected, $a + $b);
    }

    public static function additionProvider(): array
    {
        return [
            'positive numbers' => [2, 3, 5],
            'negative numbers' => [-2, -3, -5],
            'mixed signs' => [-2, 3, 1],
            'zero' => [0, 0, 0],
        ];
    }
}
```

**Test setup and teardown:**
```php
<?php

class DatabaseTest extends TestCase
{
    private Database $db;

    protected function setUp(): void
    {
        parent::setUp();
        $this->db = new Database('test.db');
        $this->db->migrate();
    }

    protected function tearDown(): void
    {
        $this->db->drop();
        parent::tearDown();
    }

    public function test_can_insert_user(): void
    {
        $user = $this->db->insert('users', [
            'name' => 'John',
            'email' => 'john@example.com'
        ]);

        $this->assertNotNull($user->id);
    }
}
```

**Mocking:**
```php
<?php

class UserServiceTest extends TestCase
{
    public function test_find_user_calls_repository(): void
    {
        $repository = $this->createMock(UserRepository::class);
        $repository->expects($this->once())
            ->method('find')
            ->with($this->equalTo(123))
            ->willReturn(new User(123, 'John'));

        $service = new UserService($repository);
        $user = $service->findUser(123);

        $this->assertEquals('John', $user->getName());
    }
}
```

**Pest testing framework:**
```php
<?php

use App\Services\Calculator;

it('adds two numbers', function () {
    $calculator = new Calculator();
    $result = $calculator->add(2, 3);

    expect($result)->toBe(5);
});

it('throws exception when dividing by zero', function () {
    $calculator = new Calculator();
    $calculator->divide(10, 0);
})->throws(DivisionByZeroError::class);

test('multiplication', function () {
    expect((new Calculator())->multiply(3, 4))->toBe(12);
});
```

### Running Tests

**Run all tests:**
```bash
./vendor/bin/phpunit
```

**Run specific test file:**
```bash
./vendor/bin/phpunit tests/Unit/CalculatorTest.php
```

**Run specific test method:**
```bash
./vendor/bin/phpunit --filter test_add_two_numbers
```

**Run with verbose output:**
```bash
./vendor/bin/phpunit --verbose
```

**Run tests in parallel (with ParaTest):**
```bash
composer require --dev brianium/paratest
./vendor/bin/paratest
```

**Pest commands:**
```bash
./vendor/bin/pest
./vendor/bin/pest --filter test_name
./vendor/bin/pest --parallel
```

### Code Coverage

**Generate coverage report:**
```bash
./vendor/bin/phpunit --coverage-html coverage
```

**Coverage with specific format:**
```bash
# HTML
./vendor/bin/phpunit --coverage-html coverage

# Clover XML
./vendor/bin/phpunit --coverage-clover coverage.xml

# Text
./vendor/bin/phpunit --coverage-text
```

**PHPUnit configuration (`phpunit.xml`):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit bootstrap="vendor/autoload.php"
         colors="true"
         stopOnFailure="false">
    <testsuites>
        <testsuite name="Unit">
            <directory>tests/Unit</directory>
        </testsuite>
        <testsuite name="Feature">
            <directory>tests/Feature</directory>
        </testsuite>
    </testsuites>
    <coverage>
        <include>
            <directory suffix=".php">src</directory>
        </include>
    </coverage>
</phpunit>
```

---

## Security

### Security Scanners

Auto Code integrates these security tools for PHP projects:

| Tool | Purpose | Usage |
|------|---------|-------|
| **Psalm** | Static analysis & security | `./vendor/bin/psalm --taint-analysis` |
| **PHPStan** | Static analysis | `./vendor/bin/phpstan analyse` |
| **Rector** | Code quality & modernization | `./vendor/bin/rector process` |
| **PHP_CodeSniffer** | Code style & security | `./vendor/bin/phpcs` |
| **PHPMD** | Mess detector | `./vendor/bin/phpmd src text cleancode` |
| **Local PHP Security Checker** | Known vulnerability scanner | `local-php-security-checker` |

**Install security tools:**
```bash
# Psalm
composer require --dev vimeo/psalm

# PHPStan
composer require --dev phpstan/phpstan

# Rector
composer require --dev rector/rector

# PHP_CodeSniffer
composer require --dev squizlabs/php_codesniffer

# PHPMD
composer require --dev phpmd/phpmd

# Local PHP Security Checker
brew install local-php-security-checker
# or download from https://github.com/fabpot/local-php-security-checker
```

### Common Vulnerabilities

**Dangerous patterns to avoid:**

- SQL injection - Use prepared statements, never concatenate SQL
- XSS (Cross-Site Scripting) - Escape output, sanitize input
- CSRF (Cross-Site Request Forgery) - Use CSRF tokens
- Command injection - Avoid `exec()`, `shell_exec()`, `system()`
- File inclusion - Validate file paths, never use user input directly
- Insecure deserialization - Avoid `unserialize()` on untrusted data
- Weak cryptography - Use `password_hash()`, not MD5/SHA1
- Session fixation - Regenerate session IDs after login
- Directory traversal - Validate and sanitize file paths
- Insecure file uploads - Validate file types, move outside web root

### Best Practices

**✅ DO:**

1. **Use prepared statements for SQL:**
   ```php
   <?php

   // ✅ CORRECT - Prepared statement
   $stmt = $pdo->prepare('SELECT * FROM users WHERE id = :id');
   $stmt->execute(['id' => $userId]);
   $user = $stmt->fetch();

   // With query builder (Laravel)
   $user = DB::table('users')->where('id', $userId)->first();
   ```

2. **Escape output to prevent XSS:**
   ```php
   <?php

   // ✅ CORRECT - Escaped output
   echo htmlspecialchars($userInput, ENT_QUOTES, 'UTF-8');

   // In templates (Laravel Blade)
   {{ $userInput }}  // Auto-escaped
   {!! $trustedHtml !!}  // Unescaped (use with caution)
   ```

3. **Use password_hash for passwords:**
   ```php
   <?php

   // ✅ CORRECT - Secure password hashing
   $hash = password_hash($password, PASSWORD_ARGON2ID);

   // Verify
   if (password_verify($inputPassword, $hash)) {
       // Password is correct
   }
   ```

4. **Validate and sanitize input:**
   ```php
   <?php

   $email = filter_var($input, FILTER_VALIDATE_EMAIL);
   if ($email === false) {
       throw new ValidationException('Invalid email');
   }

   // Or use validation library
   $validated = $validator->validate($input, [
       'email' => 'required|email',
       'age' => 'required|integer|min:18',
   ]);
   ```

5. **Use CSRF protection:**
   ```php
   <?php

   // Laravel automatically includes CSRF protection
   // In forms:
   ?>
   <form method="POST" action="/users">
       @csrf
       <!-- form fields -->
   </form>
   ```

6. **Secure file uploads:**
   ```php
   <?php

   if (!isset($_FILES['upload'])) {
       throw new Exception('No file uploaded');
   }

   $file = $_FILES['upload'];

   // Validate file type
   $allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
   if (!in_array($file['type'], $allowedTypes)) {
       throw new Exception('Invalid file type');
   }

   // Validate file size (5MB max)
   if ($file['size'] > 5 * 1024 * 1024) {
       throw new Exception('File too large');
   }

   // Generate safe filename
   $extension = pathinfo($file['name'], PATHINFO_EXTENSION);
   $filename = bin2hex(random_bytes(16)) . '.' . $extension;

   // Move to safe location outside web root
   move_uploaded_file($file['tmp_name'], '/var/uploads/' . $filename);
   ```

**❌ DON'T:**

1. **Don't use string concatenation for SQL:**
   ```php
   <?php

   // ❌ WRONG - SQL injection risk
   $query = "SELECT * FROM users WHERE name = '" . $username . "'";

   // ✅ CORRECT - Prepared statement
   $stmt = $pdo->prepare('SELECT * FROM users WHERE name = :name');
   $stmt->execute(['name' => $username]);
   ```

2. **Don't output unescaped user input:**
   ```php
   <?php

   // ❌ WRONG - XSS vulnerability
   echo $userInput;

   // ✅ CORRECT - Escaped output
   echo htmlspecialchars($userInput, ENT_QUOTES, 'UTF-8');
   ```

3. **Don't use MD5 or SHA1 for passwords:**
   ```php
   <?php

   // ❌ WRONG - Weak hashing
   $hash = md5($password);
   $hash = sha1($password);

   // ✅ CORRECT - Strong hashing
   $hash = password_hash($password, PASSWORD_ARGON2ID);
   ```

4. **Don't execute shell commands with user input:**
   ```php
   <?php

   // ❌ WRONG - Command injection risk
   exec("ls " . $userInput);
   system("rm " . $filename);

   // ✅ CORRECT - Avoid shell commands or use escapeshellarg
   $safeInput = escapeshellarg($userInput);
   exec("ls " . $safeInput);

   // Better: Use PHP functions instead
   $files = scandir($directory);
   unlink($filename);
   ```

5. **Don't use unserialize on untrusted data:**
   ```php
   <?php

   // ❌ WRONG - Object injection risk
   $data = unserialize($_COOKIE['data']);

   // ✅ CORRECT - Use JSON
   $data = json_decode($_COOKIE['data'], true);
   ```

---

## Framework-Specific Patterns

### Laravel

**Controller:**
```php
<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class UserController extends Controller
{
    public function index(): JsonResponse
    {
        $users = User::all();
        return response()->json($users);
    }

    public function show(int $id): JsonResponse
    {
        $user = User::findOrFail($id);
        return response()->json($user);
    }

    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|email|unique:users',
        ]);

        $user = User::create($validated);
        return response()->json($user, 201);
    }
}
```

**Eloquent model:**
```php
<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class User extends Model
{
    protected $fillable = ['name', 'email'];

    protected $casts = [
        'email_verified_at' => 'datetime',
    ];

    public function posts(): HasMany
    {
        return $this->hasMany(Post::class);
    }
}
```

**Routes:**
```php
<?php

use App\Http\Controllers\UserController;
use Illuminate\Support\Facades\Route;

Route::get('/users', [UserController::class, 'index']);
Route::get('/users/{id}', [UserController::class, 'show']);
Route::post('/users', [UserController::class, 'store']);
Route::put('/users/{id}', [UserController::class, 'update']);
Route::delete('/users/{id}', [UserController::class, 'destroy']);

// Or use resource route
Route::apiResource('users', UserController::class);
```

**Middleware:**
```php
<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class CheckAdmin
{
    public function handle(Request $request, Closure $next)
    {
        if (!$request->user()->isAdmin()) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        return $next($request);
    }
}
```

### Symfony

**Controller:**
```php
<?php

namespace App\Controller;

use App\Entity\User;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;

#[Route('/api/users')]
class UserController extends AbstractController
{
    #[Route('', methods: ['GET'])]
    public function index(EntityManagerInterface $em): JsonResponse
    {
        $users = $em->getRepository(User::class)->findAll();
        return $this->json($users);
    }

    #[Route('/{id}', methods: ['GET'])]
    public function show(int $id, EntityManagerInterface $em): JsonResponse
    {
        $user = $em->getRepository(User::class)->find($id);

        if (!$user) {
            return $this->json(['error' => 'User not found'], Response::HTTP_NOT_FOUND);
        }

        return $this->json($user);
    }

    #[Route('', methods: ['POST'])]
    public function create(Request $request, EntityManagerInterface $em): JsonResponse
    {
        $data = json_decode($request->getContent(), true);

        $user = new User();
        $user->setName($data['name']);
        $user->setEmail($data['email']);

        $em->persist($user);
        $em->flush();

        return $this->json($user, Response::HTTP_CREATED);
    }
}
```

**Entity:**
```php
<?php

namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'users')]
class User
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private int $id;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name;

    #[ORM\Column(type: 'string', length: 255, unique: true)]
    private string $email;

    public function getId(): int
    {
        return $this->id;
    }

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): void
    {
        $this->name = $name;
    }
}
```

### CodeIgniter

**Controller:**
```php
<?php

namespace App\Controllers;

use App\Models\UserModel;
use CodeIgniter\HTTP\ResponseInterface;
use CodeIgniter\RESTful\ResourceController;

class User extends ResourceController
{
    protected $modelName = UserModel::class;
    protected $format = 'json';

    public function index(): ResponseInterface
    {
        $users = $this->model->findAll();
        return $this->respond($users);
    }

    public function show($id = null): ResponseInterface
    {
        $user = $this->model->find($id);

        if (!$user) {
            return $this->failNotFound('User not found');
        }

        return $this->respond($user);
    }

    public function create(): ResponseInterface
    {
        $data = $this->request->getJSON(true);

        if (!$this->model->save($data)) {
            return $this->failValidationErrors($this->model->errors());
        }

        return $this->respondCreated(['id' => $this->model->getInsertID()]);
    }
}
```

**Model:**
```php
<?php

namespace App\Models;

use CodeIgniter\Model;

class UserModel extends Model
{
    protected $table = 'users';
    protected $primaryKey = 'id';
    protected $allowedFields = ['name', 'email'];

    protected $validationRules = [
        'name' => 'required|min_length[3]|max_length[255]',
        'email' => 'required|valid_email|is_unique[users.email]',
    ];
}
```

### Slim

**Application setup:**
```php
<?php

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Factory\AppFactory;

require __DIR__ . '/vendor/autoload.php';

$app = AppFactory::create();

// Routes
$app->get('/users', function (Request $request, Response $response) {
    $users = getUsersFromDatabase();
    $response->getBody()->write(json_encode($users));
    return $response->withHeader('Content-Type', 'application/json');
});

$app->get('/users/{id}', function (Request $request, Response $response, array $args) {
    $user = getUserById((int)$args['id']);

    if (!$user) {
        return $response->withStatus(404)
            ->withHeader('Content-Type', 'application/json')
            ->getBody()->write(json_encode(['error' => 'User not found']));
    }

    $response->getBody()->write(json_encode($user));
    return $response->withHeader('Content-Type', 'application/json');
});

$app->post('/users', function (Request $request, Response $response) {
    $data = $request->getParsedBody();
    $user = createUser($data);

    $response->getBody()->write(json_encode($user));
    return $response->withStatus(201)
        ->withHeader('Content-Type', 'application/json');
});

$app->run();
```

**Middleware:**
```php
<?php

use Psr\Http\Message\ServerRequestInterface as Request;
use Psr\Http\Server\RequestHandlerInterface as RequestHandler;
use Slim\Psr7\Response;

$authMiddleware = function (Request $request, RequestHandler $handler) {
    $token = $request->getHeaderLine('Authorization');

    if (!validateToken($token)) {
        $response = new Response();
        $response->getBody()->write(json_encode(['error' => 'Unauthorized']));
        return $response->withStatus(401)
            ->withHeader('Content-Type', 'application/json');
    }

    return $handler->handle($request);
};

$app->add($authMiddleware);
```

---

## Code Generation

Auto Code generates idiomatic PHP code based on your project context:

1. **Framework detection** - Automatically detects Laravel, Symfony, CodeIgniter, Slim from `composer.json`
2. **Modern PHP** - Uses PHP 8.1+ features (enums, readonly, constructor promotion, named arguments)
3. **Type safety** - Strict types, proper type hints for parameters and return values
4. **PSR compliance** - Follows PSR-1, PSR-2, PSR-4, PSR-12 standards
5. **Testing** - PHPUnit or Pest tests with proper assertions and mocking
6. **Security** - Avoids dangerous functions, uses prepared statements, escapes output
7. **Error handling** - Custom exceptions, proper try-catch blocks

**Example spec:**
```markdown
# Feature: User Authentication API

Create a REST API for user authentication with JWT tokens.

## Requirements
- POST /auth/register - Register new user
- POST /auth/login - Login and receive JWT
- GET /auth/profile - Get user profile (authenticated)

## Tech Stack
- Framework: Laravel 10
- Database: MySQL with Eloquent ORM
- Authentication: JWT with tymon/jwt-auth
```

Auto Code will:
- Detect Laravel framework from `composer.json`
- Generate controllers using Laravel patterns
- Use Eloquent models with proper relationships
- Include validation rules
- Add middleware for JWT authentication
- Generate PHPUnit tests for all endpoints
- Follow Laravel coding standards
- Use type hints and return types throughout

---

## Additional Resources

- [PHP Official Documentation](https://www.php.net/docs.php)
- [PHP: The Right Way](https://phptherightway.com/)
- [PHP Standards Recommendations (PSR)](https://www.php-fig.org/psr/)
- [Laravel Documentation](https://laravel.com/docs)
- [Symfony Documentation](https://symfony.com/doc/current/index.html)
- [Composer Documentation](https://getcomposer.org/doc/)
- [PHPUnit Documentation](https://phpunit.de/documentation.html)
- [Psalm](https://psalm.dev/)
- [PHPStan](https://phpstan.org/)

---

**Need help?** Check the [Troubleshooting Guide](../guides/TROUBLESHOOTING.md) or open an issue on GitHub.
