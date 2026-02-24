"""
PHP Language Patterns Module
=============================

Idiomatic PHP code patterns for code generation and analysis.
"""


# =============================================================================
# ERROR HANDLING PATTERNS
# =============================================================================

ERROR_HANDLING_PATTERNS = {
    "try_catch_basic": """try {
    $result = riskyOperation();
} catch (Exception $e) {
    error_log($e->getMessage());
    throw $e;
}""",
    "try_catch_multiple": """try {
    $result = operation();
} catch (InvalidArgumentException $e) {
    // Handle invalid argument
    throw new AppException("Invalid input", 0, $e);
} catch (RuntimeException $e) {
    // Handle runtime error
    log_error($e);
} catch (Exception $e) {
    // Handle all other exceptions
    throw $e;
}""",
    "custom_exception": """class AppException extends Exception
{
    private array $context;

    public function __construct(
        string $message = "",
        int $code = 0,
        ?Throwable $previous = null,
        array $context = []
    ) {
        parent::__construct($message, $code, $previous);
        $this->context = $context;
    }

    public function getContext(): array
    {
        return $this->context;
    }
}""",
    "exception_hierarchy": """class NotFoundException extends AppException {}
class ValidationException extends AppException {}
class UnauthorizedException extends AppException {}

// Usage
if (!$user) {
    throw new NotFoundException("User not found", 404);
}""",
    "finally_cleanup": """$file = null;
try {
    $file = fopen('file.txt', 'r');
    $content = fread($file, filesize('file.txt'));
} catch (Exception $e) {
    error_log($e->getMessage());
} finally {
    if ($file !== null) {
        fclose($file);
    }
}""",
}


# =============================================================================
# OOP PATTERNS
# =============================================================================

OOP_PATTERNS = {
    "class_basic": """class User
{
    private int $id;
    private string $name;
    private string $email;

    public function __construct(int $id, string $name, string $email)
    {
        $this->id = $id;
        $this->name = $name;
        $this->email = $email;
    }

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): void
    {
        $this->name = $name;
    }
}""",
    "interface_implementation": """interface LoggerInterface
{
    public function log(string $message): void;
    public function error(string $message): void;
}

class FileLogger implements LoggerInterface
{
    private string $logFile;

    public function __construct(string $logFile)
    {
        $this->logFile = $logFile;
    }

    public function log(string $message): void
    {
        file_put_contents($this->logFile, $message . PHP_EOL, FILE_APPEND);
    }

    public function error(string $message): void
    {
        $this->log('[ERROR] ' . $message);
    }
}""",
    "trait_usage": """trait Timestampable
{
    protected ?DateTime $createdAt = null;
    protected ?DateTime $updatedAt = null;

    public function setCreatedAt(DateTime $dateTime): void
    {
        $this->createdAt = $dateTime;
    }

    public function setUpdatedAt(DateTime $dateTime): void
    {
        $this->updatedAt = $dateTime;
    }

    public function touch(): void
    {
        $this->updatedAt = new DateTime();
    }
}

class Article
{
    use Timestampable;

    private string $title;
    private string $content;
}""",
    "abstract_class": """abstract class BaseRepository
{
    protected PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    abstract protected function getTableName(): string;

    public function find(int $id): ?array
    {
        $stmt = $this->db->prepare(
            "SELECT * FROM {$this->getTableName()} WHERE id = ?"
        );
        $stmt->execute([$id]);
        return $stmt->fetch(PDO::FETCH_ASSOC) ?: null;
    }
}

class UserRepository extends BaseRepository
{
    protected function getTableName(): string
    {
        return 'users';
    }
}""",
    "property_promotion": """class User
{
    public function __construct(
        private int $id,
        private string $name,
        private string $email,
        private readonly DateTime $createdAt = new DateTime()
    ) {}

    public function getId(): int
    {
        return $this->id;
    }
}""",
    "readonly_properties": """class Config
{
    public function __construct(
        public readonly string $host,
        public readonly int $port,
        public readonly string $database
    ) {}
}

$config = new Config('localhost', 5432, 'mydb');
// $config->host = 'other'; // Error: Cannot modify readonly property""",
}


# =============================================================================
# NAMESPACE AND AUTOLOADING PATTERNS
# =============================================================================

NAMESPACE_PATTERNS = {
    "namespace_declaration": """<?php

namespace App\\Services;

use App\\Models\\User;
use App\\Exceptions\\NotFoundException;
use Psr\\Log\\LoggerInterface;

class UserService
{
    private LoggerInterface $logger;

    public function __construct(LoggerInterface $logger)
    {
        $this->logger = $logger;
    }
}""",
    "namespace_aliasing": """use App\\Services\\Payment\\PayPalService;
use App\\Services\\Payment\\StripeService as Stripe;
use function App\\Helpers\\format_date;
use const App\\Constants\\MAX_USERS;

$paypal = new PayPalService();
$stripe = new Stripe();""",
    "psr4_autoload": """// composer.json
{
    "autoload": {
        "psr-4": {
            "App\\\\": "src/",
            "Tests\\\\": "tests/"
        }
    }
}

// File: src/Services/UserService.php
namespace App\\Services;

class UserService
{
    // automatically loaded
}""",
}


# =============================================================================
# TYPE HINTING PATTERNS
# =============================================================================

TYPE_PATTERNS = {
    "strict_types": """<?php

declare(strict_types=1);

namespace App\\Services;

class Calculator
{
    public function add(int $a, int $b): int
    {
        return $a + $b;
    }
}

// $calc->add('1', '2'); // TypeError in strict mode""",
    "nullable_types": """function findUser(?int $id): ?User
{
    if ($id === null) {
        return null;
    }

    return $this->repository->find($id);
}""",
    "union_types": """function process(int|float $number): int|float
{
    return $number * 2;
}

function handleInput(array|Collection $data): void
{
    // handle both arrays and collections
}""",
    "mixed_type": """function transform(mixed $value): mixed
{
    if (is_array($value)) {
        return array_map(fn($v) => $v * 2, $value);
    }
    return $value;
}""",
    "return_type_void": """function logMessage(string $message): void
{
    file_put_contents('log.txt', $message . PHP_EOL, FILE_APPEND);
}""",
    "return_type_never": """function terminate(string $message): never
{
    throw new RuntimeException($message);
}""",
}


# =============================================================================
# ARRAY AND COLLECTION PATTERNS
# =============================================================================

ARRAY_PATTERNS = {
    "array_creation": """// Indexed array
$numbers = [1, 2, 3, 4, 5];

// Associative array
$user = [
    'id' => 1,
    'name' => 'John Doe',
    'email' => 'john@example.com',
];

// Nested array
$config = [
    'database' => [
        'host' => 'localhost',
        'port' => 5432,
    ],
];""",
    "array_functions": """$numbers = [1, 2, 3, 4, 5];

// Map
$doubled = array_map(fn($n) => $n * 2, $numbers);

// Filter
$evens = array_filter($numbers, fn($n) => $n % 2 === 0);

// Reduce
$sum = array_reduce($numbers, fn($carry, $n) => $carry + $n, 0);

// Find
$found = array_filter($users, fn($u) => $u->id === 1)[0] ?? null;""",
    "spread_operator": """$defaults = ['host' => 'localhost', 'port' => 8080];
$custom = ['port' => 3000];

$config = [...$defaults, ...$custom];
// Result: ['host' => 'localhost', 'port' => 3000]""",
    "destructuring": """[$name, $email] = getUserData();

['name' => $userName, 'email' => $userEmail] = $user;

// Skip values
[, , $third] = [1, 2, 3, 4];""",
}


# =============================================================================
# DATABASE PATTERNS (PDO)
# =============================================================================

DATABASE_PATTERNS = {
    "pdo_connection": """$dsn = 'mysql:host=localhost;dbname=mydb;charset=utf8mb4';
$options = [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES => false,
];

$pdo = new PDO($dsn, 'username', 'password', $options);""",
    "prepared_statement": """$stmt = $pdo->prepare('SELECT * FROM users WHERE email = ?');
$stmt->execute([$email]);
$user = $stmt->fetch();

// Named parameters
$stmt = $pdo->prepare('SELECT * FROM users WHERE email = :email');
$stmt->execute(['email' => $email]);
$user = $stmt->fetch();""",
    "insert_with_id": """$stmt = $pdo->prepare(
    'INSERT INTO users (name, email) VALUES (?, ?)'
);
$stmt->execute([$name, $email]);
$userId = $pdo->lastInsertId();""",
    "transaction": """try {
    $pdo->beginTransaction();

    $stmt = $pdo->prepare('UPDATE accounts SET balance = balance - ? WHERE id = ?');
    $stmt->execute([$amount, $fromAccount]);

    $stmt = $pdo->prepare('UPDATE accounts SET balance = balance + ? WHERE id = ?');
    $stmt->execute([$amount, $toAccount]);

    $pdo->commit();
} catch (Exception $e) {
    $pdo->rollBack();
    throw $e;
}""",
    "fetch_all": """$stmt = $pdo->query('SELECT * FROM users');
$users = $stmt->fetchAll();

// Fetch as objects
$users = $stmt->fetchAll(PDO::FETCH_CLASS, User::class);""",
}


# =============================================================================
# TESTING PATTERNS (PHPUNIT)
# =============================================================================

TESTING_PATTERNS = {
    "basic_test": """use PHPUnit\\Framework\\TestCase;

class CalculatorTest extends TestCase
{
    public function testAdd(): void
    {
        $calculator = new Calculator();
        $result = $calculator->add(2, 3);

        $this->assertEquals(5, $result);
    }

    public function testDivideByZero(): void
    {
        $this->expectException(DivisionByZeroError::class);

        $calculator = new Calculator();
        $calculator->divide(10, 0);
    }
}""",
    "data_provider": """class UserValidatorTest extends TestCase
{
    /**
     * @dataProvider emailProvider
     */
    public function testEmailValidation(string $email, bool $expected): void
    {
        $validator = new UserValidator();
        $result = $validator->isValidEmail($email);

        $this->assertEquals($expected, $result);
    }

    public function emailProvider(): array
    {
        return [
            ['valid@example.com', true],
            ['invalid', false],
            ['@example.com', false],
        ];
    }
}""",
    "mock_objects": """class UserServiceTest extends TestCase
{
    public function testGetUser(): void
    {
        $repository = $this->createMock(UserRepository::class);
        $repository->method('find')
            ->with(1)
            ->willReturn(new User(1, 'John', 'john@example.com'));

        $service = new UserService($repository);
        $user = $service->getUser(1);

        $this->assertEquals('John', $user->getName());
    }
}""",
    "test_setup_teardown": """class DatabaseTest extends TestCase
{
    private PDO $pdo;

    protected function setUp(): void
    {
        $this->pdo = new PDO('sqlite::memory:');
        $this->pdo->exec('CREATE TABLE users (id INT, name TEXT)');
    }

    protected function tearDown(): void
    {
        $this->pdo = null;
    }

    public function testInsertUser(): void
    {
        $stmt = $this->pdo->prepare('INSERT INTO users VALUES (?, ?)');
        $result = $stmt->execute([1, 'John']);

        $this->assertTrue($result);
    }
}""",
}


# =============================================================================
# FRAMEWORK-SPECIFIC PATTERNS (LARAVEL)
# =============================================================================

LARAVEL_PATTERNS = {
    "eloquent_model": """namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;
use Illuminate\\Database\\Eloquent\\Relations\\HasMany;

class User extends Model
{
    protected $fillable = ['name', 'email'];

    protected $casts = [
        'email_verified_at' => 'datetime',
        'is_admin' => 'boolean',
    ];

    public function posts(): HasMany
    {
        return $this->hasMany(Post::class);
    }
}""",
    "controller": """namespace App\\Http\\Controllers;

use App\\Models\\User;
use Illuminate\\Http\\JsonResponse;
use Illuminate\\Http\\Request;

class UserController extends Controller
{
    public function index(): JsonResponse
    {
        $users = User::all();
        return response()->json($users);
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
}""",
    "service_container": """namespace App\\Providers;

use App\\Services\\PaymentService;
use App\\Services\\PayPalService;
use Illuminate\\Support\\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(PaymentService::class, function ($app) {
            return new PayPalService($app->make('config')->get('paypal'));
        });
    }
}""",
    "middleware": """namespace App\\Http\\Middleware;

use Closure;
use Illuminate\\Http\\Request;

class EnsureUserIsAdmin
{
    public function handle(Request $request, Closure $next)
    {
        if (!$request->user() || !$request->user()->is_admin) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        return $next($request);
    }
}""",
    "route_definition": """use App\\Http\\Controllers\\UserController;

Route::get('/api/users', [UserController::class, 'index']);
Route::post('/api/users', [UserController::class, 'store']);

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'show']);
    Route::put('/profile', [ProfileController::class, 'update']);
});""",
    "eloquent_query": """// Find by ID
$user = User::find(1);

// Where clause
$users = User::where('is_admin', true)
    ->where('created_at', '>', now()->subDays(30))
    ->get();

// Eager loading
$users = User::with('posts')->get();

// Pagination
$users = User::paginate(15);

// Create
$user = User::create([
    'name' => 'John Doe',
    'email' => 'john@example.com',
]);""",
}


# =============================================================================
# FRAMEWORK-SPECIFIC PATTERNS (SYMFONY)
# =============================================================================

SYMFONY_PATTERNS = {
    "controller": """namespace App\\Controller;

use Symfony\\Bundle\\FrameworkBundle\\Controller\\AbstractController;
use Symfony\\Component\\HttpFoundation\\JsonResponse;
use Symfony\\Component\\HttpFoundation\\Request;
use Symfony\\Component\\Routing\\Annotation\\Route;

class UserController extends AbstractController
{
    #[Route('/api/users', methods: ['GET'])]
    public function index(): JsonResponse
    {
        $users = $this->getDoctrine()
            ->getRepository(User::class)
            ->findAll();

        return $this->json($users);
    }

    #[Route('/api/users', methods: ['POST'])]
    public function create(Request $request): JsonResponse
    {
        $data = json_decode($request->getContent(), true);

        // Create user logic

        return $this->json($user, 201);
    }
}""",
    "service_definition": """# config/services.yaml
services:
    App\\Service\\UserService:
        arguments:
            $repository: '@App\\Repository\\UserRepository'
            $logger: '@logger'

# PHP class
namespace App\\Service;

use Psr\\Log\\LoggerInterface;

class UserService
{
    public function __construct(
        private UserRepository $repository,
        private LoggerInterface $logger
    ) {}
}""",
    "doctrine_entity": """namespace App\\Entity;

use Doctrine\\ORM\\Mapping as ORM;

#[ORM\\Entity(repositoryClass: UserRepository::class)]
#[ORM\\Table(name: 'users')]
class User
{
    #[ORM\\Id]
    #[ORM\\GeneratedValue]
    #[ORM\\Column(type: 'integer')]
    private int $id;

    #[ORM\\Column(type: 'string', length: 255)]
    private string $name;

    #[ORM\\Column(type: 'string', unique: true)]
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
}""",
    "event_listener": """namespace App\\EventListener;

use Symfony\\Component\\HttpKernel\\Event\\RequestEvent;

class RequestListener
{
    public function onKernelRequest(RequestEvent $event): void
    {
        $request = $event->getRequest();

        // Process request
    }
}

# config/services.yaml
services:
    App\\EventListener\\RequestListener:
        tags:
            - { name: kernel.event_listener, event: kernel.request }""",
}


# =============================================================================
# MODERN PHP PATTERNS
# =============================================================================

MODERN_PATTERNS = {
    "arrow_functions": """$numbers = [1, 2, 3, 4, 5];

$doubled = array_map(fn($n) => $n * 2, $numbers);

$evens = array_filter($numbers, fn($n) => $n % 2 === 0);

$sum = array_reduce($numbers, fn($carry, $n) => $carry + $n, 0);""",
    "match_expression": """$result = match ($status) {
    'pending' => 'Waiting for approval',
    'approved' => 'Order confirmed',
    'shipped' => 'On the way',
    'delivered' => 'Completed',
    default => 'Unknown status',
};

// With conditions
$category = match (true) {
    $age < 13 => 'child',
    $age < 18 => 'teenager',
    $age < 65 => 'adult',
    default => 'senior',
};""",
    "named_arguments": """function createUser(
    string $name,
    string $email,
    bool $isAdmin = false,
    ?DateTime $createdAt = null
): User {
    // implementation
}

$user = createUser(
    name: 'John Doe',
    email: 'john@example.com',
    isAdmin: true
);""",
    "nullsafe_operator": """$country = $user?->getAddress()?->getCountry();

// Equivalent to:
$country = null;
if ($user !== null) {
    $address = $user->getAddress();
    if ($address !== null) {
        $country = $address->getCountry();
    }
}""",
    "attributes": """#[Route('/api/users', methods: ['GET'])]
#[Cache(ttl: 3600)]
#[RequiresAuth]
class UserController
{
    #[Validate(['email' => 'required|email'])]
    public function create(Request $request): Response
    {
        // implementation
    }
}""",
    "enums": """enum Status: string
{
    case PENDING = 'pending';
    case APPROVED = 'approved';
    case REJECTED = 'rejected';

    public function label(): string
    {
        return match($this) {
            self::PENDING => 'Pending Approval',
            self::APPROVED => 'Approved',
            self::REJECTED => 'Rejected',
        };
    }
}

$status = Status::PENDING;
echo $status->label(); // "Pending Approval\"""",
}


# =============================================================================
# DEPENDENCY INJECTION PATTERNS
# =============================================================================

DEPENDENCY_INJECTION_PATTERNS = {
    "constructor_injection": """class UserService
{
    public function __construct(
        private UserRepository $repository,
        private LoggerInterface $logger,
        private EventDispatcher $dispatcher
    ) {}

    public function createUser(array $data): User
    {
        $this->logger->info('Creating user');

        $user = $this->repository->create($data);

        $this->dispatcher->dispatch(new UserCreated($user));

        return $user;
    }
}""",
    "interface_dependency": """interface PaymentGateway
{
    public function charge(int $amount): PaymentResult;
}

class StripeGateway implements PaymentGateway
{
    public function charge(int $amount): PaymentResult
    {
        // Stripe implementation
    }
}

class PaymentService
{
    public function __construct(
        private PaymentGateway $gateway
    ) {}

    public function processPayment(Order $order): void
    {
        $this->gateway->charge($order->getTotal());
    }
}""",
}


# =============================================================================
# COMBINED PATTERNS EXPORT
# =============================================================================

PHP_PATTERNS = {
    "error_handling": ERROR_HANDLING_PATTERNS,
    "oop": OOP_PATTERNS,
    "namespaces": NAMESPACE_PATTERNS,
    "types": TYPE_PATTERNS,
    "arrays": ARRAY_PATTERNS,
    "database": DATABASE_PATTERNS,
    "testing": TESTING_PATTERNS,
    "modern": MODERN_PATTERNS,
    "dependency_injection": DEPENDENCY_INJECTION_PATTERNS,
    "frameworks": {
        "laravel": LARAVEL_PATTERNS,
        "symfony": SYMFONY_PATTERNS,
    },
}


__all__ = ["PHP_PATTERNS"]
