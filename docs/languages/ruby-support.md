# Ruby Language Support

Auto Code provides first-class support for Ruby development with idiomatic code generation, framework detection, security scanning, and testing integration.

## Table of Contents

- [Setup](#setup)
  - [Ruby Installation](#ruby-installation)
  - [Project Setup](#project-setup)
  - [Dependency Management](#dependency-management)
- [Supported Frameworks](#supported-frameworks)
- [Idiomatic Patterns](#idiomatic-patterns)
  - [Error Handling](#error-handling)
  - [Object-Oriented Patterns](#object-oriented-patterns)
  - [Blocks and Iterators](#blocks-and-iterators)
  - [Metaprogramming](#metaprogramming)
  - [Collections](#collections)
  - [String Manipulation](#string-manipulation)
  - [File I/O](#file-io)
- [Testing](#testing)
  - [Test Patterns](#test-patterns)
  - [Running Tests](#running-tests)
- [Security](#security)
  - [Security Scanners](#security-scanners)
  - [Common Vulnerabilities](#common-vulnerabilities)
  - [Best Practices](#best-practices)
- [Framework-Specific Patterns](#framework-specific-patterns)
  - [Ruby on Rails](#ruby-on-rails)
  - [Sinatra](#sinatra)
- [Code Generation](#code-generation)

---

## Setup

### Ruby Installation

Install Ruby 3.0 or later using a version manager:

**macOS/Linux (rbenv):**
```bash
# Install rbenv
brew install rbenv

# Install Ruby build plugin
brew install ruby-build

# Install latest Ruby
rbenv install 3.3.0
rbenv global 3.3.0

# Verify installation
ruby --version
```

**macOS/Linux (rvm):**
```bash
# Install RVM
\curl -sSL https://get.rvm.io | bash -s stable
source ~/.rvm/scripts/rvm

# Install Ruby
rvm install 3.3.0
rvm use 3.3.0 --default

# Verify installation
ruby --version
```

**Windows:**
Download and install [RubyInstaller](https://rubyinstaller.org/) for Windows. Choose the version with MSYS2 devkit for native extensions.

**Verify installation:**
```bash
ruby --version
gem --version
```

### Project Setup

Create a new Ruby project:

```bash
# Create project directory
mkdir my-ruby-project
cd my-ruby-project

# Create gemspec for library projects
cat > my-ruby-project.gemspec << 'EOF'
Gem::Specification.new do |spec|
  spec.name        = "my-ruby-project"
  spec.version     = "0.1.0"
  spec.authors     = ["Your Name"]
  spec.email       = ["your.email@example.com"]
  spec.summary     = "A brief summary"
  spec.description = "A longer description"
  spec.homepage    = "https://example.com"
  spec.license     = "MIT"

  spec.files         = Dir.glob("{lib}/**/*")
  spec.require_paths = ["lib"]
end
EOF

# Create lib directory structure
mkdir -p lib
cat > lib/my-ruby-project.rb << 'EOF'
module MyRubyProject
  VERSION = "0.1.0"

  def self.greet
    puts "Hello from MyRubyProject!"
  end
end
EOF

# Create main executable (optional)
mkdir -p bin
cat > bin/my-ruby-project << 'EOF'
#!/usr/bin/env ruby
require_relative '../lib/my-ruby-project'

MyRubyProject.greet
EOF
chmod +x bin/my-ruby-project
```

**Project structure:**
```
my-ruby-project/
├── lib/                        # Library code
│   └── my-ruby-project.rb      # Main module
├── bin/                        # Executables
│   └── my-ruby-project         # Main executable
├── spec/                       # Tests
│   └── spec_helper.rb
├── Gemfile                     # Development dependencies
└── my-ruby-project.gemspec     # Gem specification
```

### Dependency Management

**Create Gemfile for development dependencies:**
```ruby
# frozen_string_literal: true

source "https://rubygems.org"

# Specify your gem's dependencies in my-ruby-project.gemspec
gemspec

group :development do
  gem "rspec", "~> 3.12"
  gem "rubocop", "~> 1.50"
  gem "rubocop-performance", "~> 1.19"
end

group :test do
  gem "simplecov", "~> 0.22"
  gem "factory_bot", "~> 6.2"
end
```

**Install dependencies:**
```bash
# Install gems
bundle install

# Update gems
bundle update

# Add a gem
bundle add rspec
bundle add rubocop --group development
```

**Use gems in code:**
```ruby
# In your gemspec
spec.add_dependency "http", "~> 5.0"
spec.add_development_dependency "rspec", "~> 3.12"

# Or in Gemfile
gem "http", "~> 5.0"
```

---

## Supported Frameworks

Auto Code automatically detects and provides idiomatic patterns for these Ruby frameworks:

| Framework | Detection | Use Case |
|-----------|-----------|----------|
| **Ruby on Rails** | `Gemfile` contains `rails` | Full-stack web framework |
| **Sinatra** | `Gemfile` contains `sinatra` | Lightweight web framework |
| **Grape** | `Gemfile` contains `grape` | REST API framework |
| **Hanami** | `Gemfile` contains `hanami` | Modular web framework |
| **Rodauth** | `Gemfile` contains `rodauth` | Authentication framework |
| **Sidekiq** | `Gemfile` contains `sidekiq` | Background job processing |
| **RSpec** | `Gemfile` contains `rspec` | Testing framework |
| **Minitest** | `Gemfile` contains `minitest` | Testing framework |

---

## Idiomatic Patterns

Auto Code generates idiomatic Ruby code following community best practices.

### Error Handling

**Basic rescue:**
```ruby
begin
  operation
rescue StandardError => e
  handle_error(e)
end
```

**Rescue with else and ensure:**
```ruby
begin
  operation
rescue StandardError => e
  handle_error(e)
else
  # Runs if no exception
  success
ensure
  # Always runs
  cleanup
end
```

**Custom error classes:**
```ruby
class AppError < StandardError
  attr_reader :code, :details

  def initialize(message, code: 500, details: {})
    super(message)
    @code = code
    @details = details
  end
end

raise AppError.new("Not found", code: 404)
```

**Retry pattern:**
```ruby
attempts = 0
begin
  operation
rescue TransientError => e
  attempts += 1
  retry if attempts < 3
  raise
end
```

**Specific rescue:**
```ruby
begin
  operation
rescue ArgumentError => e
  handle_argument_error(e)
rescue IOError => e
  handle_io_error(e)
rescue StandardError => e
  handle_generic_error(e)
end
```

### Object-Oriented Patterns

**Basic class:**
```ruby
class User
  attr_accessor :name, :email
  attr_reader :id

  def initialize(name, email)
    @name = name
    @email = email
    @id = generate_id
  end

  def to_s
    "User: #{@name} (#{@email})"
  end

  private

  def generate_id
    SecureRandom.uuid
  end
end
```

**Inheritance:**
```ruby
class Animal
  def speak
    raise NotImplementedError, "Subclass must implement"
  end
end

class Dog < Animal
  def speak
    "Woof!"
  end
end

class Cat < Animal
  def speak
    "Meow!"
  end
end
```

**Module mixin:**
```ruby
module Loggable
  def log(message)
    puts "[#{Time.now}] #{message}"
  end
end

class Service
  include Loggable

  def perform
    log "Starting service"
    # work
    log "Service complete"
  end
end
```

**Singleton pattern:**
```ruby
require 'singleton'

class Configuration
  include Singleton

  attr_accessor :host, :port

  def initialize
    @host = 'localhost'
    @port = 8080
  end
end

config = Configuration.instance
```

**Struct pattern:**
```ruby
User = Struct.new(:name, :email, :role) do
  def admin?
    role == 'admin'
  end
end

user = User.new('Alice', 'alice@example.com', 'admin')
```

### Blocks and Iterators

**Basic blocks:**
```ruby
# Multi-line block (do...end)
[1, 2, 3].each do |num|
  puts num
end

# Single-line block ({...})
[1, 2, 3].each { |num| puts num }
```

**Yield pattern:**
```ruby
def with_logging
  puts "Starting"
  result = yield
  puts "Finished"
  result
end

with_logging do
  puts "Working..."
  42
end
```

**Optional block:**
```ruby
def optional_block
  if block_given?
    yield
  else
    default_behavior
  end
end
```

**Lambda and Proc:**
```ruby
# Proc
greeter = Proc.new { |name| puts "Hello, #{name}!" }
greeter.call("Alice")

# Lambda (stabby syntax)
greeter = ->(name) { puts "Hello, #{name}!" }
greeter.call("Bob")

# Lambda with multiple arguments
add = ->(a, b) { a + b }
result = add.call(2, 3)
```

**Map, select, reduce:**
```ruby
# Map
squared = [1, 2, 3].map { |n| n ** 2 }

# Select/Filter
evens = [1, 2, 3, 4].select { |n| n.even? }

# Reduce
sum = [1, 2, 3, 4].reduce(0) { |acc, n| acc + n }
# or
sum = [1, 2, 3, 4].reduce(:+)

# Symbol to proc
names = users.map(&:name)
uppercase = names.map(&:upcase)
```

### Metaprogramming

**method_missing:**
```ruby
class DynamicAttributes
  def initialize
    @attributes = {}
  end

  def method_missing(method, *args)
    method_name = method.to_s

    if method_name.end_with?('=')
      @attributes[method_name.chop.to_sym] = args.first
    elsif @attributes.key?(method.to_sym)
      @attributes[method.to_sym]
    else
      super
    end
  end

  def respond_to_missing?(method, include_private = false)
    method.to_s.end_with?('=') || @attributes.key?(method.to_sym) || super
  end
end
```

**define_method:**
```ruby
class User
  ATTRIBUTES = [:name, :email, :role]

  ATTRIBUTES.each do |attr|
    define_method(attr) do
      instance_variable_get("@#{attr}")
    end

    define_method("#{attr}=") do |value|
      instance_variable_set("@#{attr}", value)
    end
  end
end
```

**send method:**
```ruby
# Dynamic method calls
method_name = :calculate
object.send(method_name, arg1, arg2)

# Calling private methods
object.send(:private_method)
```

### Collections

**Array operations:**
```ruby
# Create
arr = [1, 2, 3]
arr = Array.new(5, 0)  # [0, 0, 0, 0, 0]

# Access
first = arr.first
last = arr.last
arr[0]
arr[-1]  # last element

# Modify
arr << 4
arr.push(5)
arr.unshift(0)  # add to beginning
arr.pop  # remove last
arr.shift  # remove first

# Iterate
arr.each { |x| puts x }
arr.each_with_index { |x, i| puts "#{i}: #{x}" }
```

**Hash operations:**
```ruby
# Create
hash = { name: 'Alice', age: 30 }
hash = Hash.new(0)  # default value

# Access
hash[:name]
hash.fetch(:email, 'default@example.com')

# Modify
hash[:role] = 'admin'
hash.merge!(other_hash)

# Iterate
hash.each { |k, v| puts "#{k}: #{v}" }
hash.each_key { |k| puts k }
hash.each_value { |v| puts v }

# Transform
hash.transform_keys(&:to_s)
hash.transform_values { |v| v.upcase }
```

**Enumerable methods:**
```ruby
# Find
users.find { |u| u.admin? }
users.find_all { |u| u.active? }

# Any/All/None
users.any?(&:admin?)
users.all?(&:valid?)
users.none?(&:banned?)

# Group
users.group_by(&:role)

# Sort
users.sort_by(&:created_at)

# Partition
active, inactive = users.partition(&:active?)
```

### String Manipulation

**Interpolation:**
```ruby
name = "Alice"
greeting = "Hello, #{name}!"

# Expression interpolation
result = "2 + 2 = #{2 + 2}"
```

**Multiline strings:**
```ruby
# Heredoc
text = <<~TEXT
  This is a multiline string
  with indentation removed
TEXT

# With interpolation
sql = <<~SQL
  SELECT * FROM users
  WHERE name = '#{name}'
SQL
```

**String methods:**
```ruby
# Case
str.upcase
str.downcase
str.capitalize
str.swapcase

# Whitespace
str.strip
str.lstrip
str.rstrip

# Search
str.include?('substring')
str.start_with?('prefix')
str.end_with?('suffix')

# Replace
str.gsub('old', 'new')
str.gsub(/pattern/, 'replacement')

# Split/Join
str.split(',')
arr.join(', ')
```

**Symbols:**
```ruby
# Symbols are immutable strings
:symbol
:'symbol with spaces'

# Common use in hashes
options = {
  host: 'localhost',
  port: 8080,
  ssl: true
}
```

### File I/O

**Reading files:**
```ruby
# Read entire file
content = File.read('file.txt')

# Read lines
lines = File.readlines('file.txt')

# Block form (auto-closes)
File.open('file.txt', 'r') do |file|
  file.each_line do |line|
    puts line
  end
end
```

**Writing files:**
```ruby
# Write entire file
File.write('file.txt', content)

# Append
File.write('file.txt', content, mode: 'a')

# Block form
File.open('file.txt', 'w') do |file|
  file.puts "Line 1"
  file.puts "Line 2"
end
```

**File operations:**
```ruby
# Check existence
File.exist?('file.txt')
File.directory?('path')

# File info
File.size('file.txt')
File.mtime('file.txt')

# Path operations
File.join('path', 'to', 'file.txt')
File.basename('/path/to/file.txt')
File.dirname('/path/to/file.txt')
File.extname('file.txt')
```

**Directory operations:**
```ruby
# List files
Dir.entries('.')
Dir.glob('*.rb')
Dir.glob('**/*.rb')  # recursive

# Create/Remove
Dir.mkdir('new_dir')
Dir.rmdir('old_dir')

# Iterate
Dir.foreach('.') do |file|
  puts file
end
```

---

## Testing

### Test Patterns

**RSpec basic test:**
```ruby
RSpec.describe Calculator do
  describe '#add' do
    it 'adds two numbers' do
      calc = Calculator.new
      result = calc.add(2, 3)
      expect(result).to eq(5)
    end

    it 'handles negative numbers' do
      calc = Calculator.new
      result = calc.add(-2, 3)
      expect(result).to eq(1)
    end
  end
end
```

**RSpec context:**
```ruby
RSpec.describe User do
  describe '#valid?' do
    context 'when all fields are present' do
      it 'returns true' do
        user = User.new(name: 'Alice', email: 'alice@example.com')
        expect(user).to be_valid
      end
    end

    context 'when email is missing' do
      it 'returns false' do
        user = User.new(name: 'Alice')
        expect(user).not_to be_valid
      end
    end
  end
end
```

**RSpec let:**
```ruby
RSpec.describe User do
  let(:user) { User.new(name: 'Alice', email: 'alice@example.com') }
  let(:admin) { User.new(name: 'Bob', email: 'bob@example.com', role: 'admin') }

  it 'has a name' do
    expect(user.name).to eq('Alice')
  end

  it 'can be an admin' do
    expect(admin).to be_admin
  end
end
```

**RSpec before/after:**
```ruby
RSpec.describe Database do
  before(:each) do
    @db = Database.new
    @db.connect
  end

  after(:each) do
    @db.disconnect
  end

  it 'can query data' do
    result = @db.query('SELECT * FROM users')
    expect(result).not_to be_empty
  end
end
```

**RSpec mocks:**
```ruby
RSpec.describe UserService do
  it 'calls the mailer' do
    mailer = double('Mailer')
    expect(mailer).to receive(:send_welcome).with('alice@example.com')

    service = UserService.new(mailer: mailer)
    service.create_user(email: 'alice@example.com')
  end
end
```

**Minitest:**
```ruby
require 'minitest/autorun'

class TestCalculator < Minitest::Test
  def setup
    @calc = Calculator.new
  end

  def test_addition
    assert_equal 5, @calc.add(2, 3)
  end

  def test_subtraction
    assert_equal 1, @calc.subtract(3, 2)
  end

  def teardown
    @calc = nil
  end
end
```

### Running Tests

**Run all RSpec tests:**
```bash
rspec
```

**Run specific test file:**
```bash
rspec spec/models/user_spec.rb
```

**Run specific test:**
```bash
rspec spec/models/user_spec.rb:42
```

**Run with documentation format:**
```bash
rspec --format documentation
```

**Run all Minitest tests:**
```bash
rake test
```

**Run specific Minitest file:**
```bash
ruby test/models/user_test.rb
```

---

## Security

### Security Scanners

Auto Code integrates these security tools for Ruby projects:

| Tool | Purpose | Usage |
|------|---------|-------|
| **bundler-audit** | Dependency vulnerability scanner | `bundle audit check --update` |
| **brakeman** | Rails security scanner | `brakeman` |
| **rubocop** | Linter and code quality | `rubocop` |
| **rubocop-security** | Security-focused linting | `rubocop --require rubocop-security` |

**Install security tools:**
```bash
# bundler-audit
gem install bundler-audit

# brakeman
gem install brakeman

# rubocop
gem install rubocop
gem install rubocop-performance
gem install rubocop-security
```

### Common Vulnerabilities

**Dangerous patterns to avoid:**

- `eval()` - Code injection risk
- `send()` with user input - Method injection
- SQL injection via string concatenation
- Command injection via backticks or `system()`
- Unsafe deserialization
- Cross-site scripting (XSS)
- Mass assignment vulnerabilities
- Insecure redirects

### Best Practices

**✅ DO:**

1. **Use prepared statements for SQL:**
   ```ruby
   # ✅ CORRECT - Rails ActiveRecord
   User.where("email = ?", email)
   User.where("name LIKE ? AND role = ?", "#{query}%", role)

   # ✅ CORRECT - Parameterized hash
   User.where(email: email, name: name)
   ```

2. **Sanitize user input:**
   ```ruby
   # ✅ CORRECT
   require 'cgi'
   sanitized = CGI.escapeHTML(user_input)
   ```

3. **Use strong parameters in Rails:**
   ```ruby
   # ✅ CORRECT
   def user_params
     params.require(:user).permit(:name, :email, :role)
   end
   ```

4. **Validate before use:**
   ```ruby
   # ✅ CORRECT
   def process_id(id)
     raise ArgumentError, "Invalid ID" unless id =~ /^\d+$/
     # process
   end
   ```

5. **Use safe YAML loading:**
   ```ruby
   # ✅ CORRECT
   require 'psych'
   data = Psych.safe_load(yaml_string, permitted_classes: [Symbol])
   ```

**❌ DON'T:**

1. **Don't use eval:**
   ```ruby
   # ❌ WRONG - Code injection
   eval(user_input)

   # ✅ CORRECT - Use send with caution
   method_name = user_input.to_sym
   object.send(method_name) if object.respond_to?(method_name)
   ```

2. **Don't interpolate SQL:**
   ```ruby
   # ❌ WRONG - SQL injection
   User.where("email = '#{email}'")

   # ✅ CORRECT
   User.where(email: email)
   ```

3. **Don't use backticks with user input:**
   ```ruby
   # ❌ WRONG - Command injection
   `ls -la #{user_input}`

   # ✅ CORRECT - Use Open3
   require 'open3'
   stdout, stderr, status = Open3.capture3('ls', '-la', user_input)
   ```

4. **Don't expose sensitive data:**
   ```ruby
   # ❌ WRONG
   puts user.password

   # ✅ CORRECT
   puts "Password: #{'*' * user.password.length}"
   ```

---

## Framework-Specific Patterns

### Ruby on Rails

**Model:**
```ruby
class User < ApplicationRecord
  # Validations
  validates :email, presence: true, uniqueness: true
  validates :name, presence: true, length: { minimum: 2 }

  # Associations
  has_many :posts, dependent: :destroy
  belongs_to :organization

  # Scopes
  scope :active, -> { where(active: true) }
  scope :recent, -> { order(created_at: :desc).limit(10) }

  # Callbacks
  before_save :normalize_email
  after_create :send_welcome_email

  private

  def normalize_email
    self.email = email.downcase.strip
  end
end
```

**Controller:**
```ruby
class UsersController < ApplicationController
  before_action :set_user, only: [:show, :update, :destroy]
  before_action :authenticate_user!

  def index
    @users = User.active.page(params[:page])
    render json: @users
  end

  def show
    render json: @user
  end

  def create
    @user = User.new(user_params)

    if @user.save
      render json: @user, status: :created
    else
      render json: @user.errors, status: :unprocessable_entity
    end
  end

  def update
    if @user.update(user_params)
      render json: @user
    else
      render json: @user.errors, status: :unprocessable_entity
    end
  end

  def destroy
    @user.destroy
    head :no_content
  end

  private

  def set_user
    @user = User.find(params[:id])
  end

  def user_params
    params.require(:user).permit(:name, :email, :role)
  end
end
```

**Migration:**
```ruby
class CreateUsers < ActiveRecord::Migration[7.0]
  def change
    create_table :users do |t|
      t.string :name, null: false
      t.string :email, null: false
      t.string :role, default: 'user'
      t.boolean :active, default: true

      t.timestamps
    end

    add_index :users, :email, unique: true
  end
end
```

**Service object:**
```ruby
class UserRegistrationService
  def initialize(user_params)
    @user_params = user_params
  end

  def call
    ActiveRecord::Base.transaction do
      user = create_user
      send_welcome_email(user)
      notify_admin(user)
      user
    end
  rescue => e
    Rails.logger.error("Registration failed: #{e.message}")
    nil
  end

  private

  def create_user
    User.create!(@user_params)
  end

  def send_welcome_email(user)
    UserMailer.welcome(user).deliver_later
  end

  def notify_admin(user)
    AdminNotifier.new_user(user).deliver_later
  end
end
```

**Concern:**
```ruby
module Searchable
  extend ActiveSupport::Concern

  included do
    scope :search, ->(query) {
      where("name LIKE ? OR email LIKE ?", "%#{query}%", "%#{query}%")
    }
  end

  class_methods do
    def fuzzy_search(term)
      # Complex search logic
    end
  end
end

class User < ApplicationRecord
  include Searchable
end
```

### Sinatra

**Basic application:**
```ruby
require 'sinatra'

get '/' do
  'Hello, World!'
end

get '/users/:id' do
  user = User.find(params[:id])
  user.to_json
end

post '/users' do
  user = User.create(JSON.parse(request.body.read))
  status 201
  user.to_json
end

put '/users/:id' do
  user = User.find(params[:id])
  user.update(JSON.parse(request.body.read))
  user.to_json
end

delete '/users/:id' do
  User.destroy(params[:id])
  status 204
end
```

**Modular application:**
```ruby
require 'sinatra/base'

class App < Sinatra::Base
  configure do
    set :server, :puma
    set :port, 4567
  end

  before do
    content_type :json
  end

  helpers do
    def authorized?
      request.env['HTTP_AUTHORIZATION'] == ENV['API_KEY']
    end
  end

  get '/protected' do
    halt 401 unless authorized?
    { message: 'Secret data' }.to_json
  end
end
```

---

## Code Generation

Auto Code generates idiomatic Ruby code based on your project context:

1. **Framework detection** - Automatically detects Rails, Sinatra, Grape from `Gemfile`
2. **Idiomatic patterns** - Follows Ruby community best practices
3. **Error handling** - Proper begin/rescue blocks with meaningful error messages
4. **Object-oriented design** - Classes, modules, and inheritance patterns
5. **Metaprogramming** - Appropriate use of Ruby's dynamic features
6. **Testing** - RSpec and Minitest patterns
7. **Security** - Avoids dangerous patterns, uses secure defaults

**Example spec:**
```markdown
# Feature: User Authentication API

Create a REST API for user authentication with JWT tokens.

## Requirements
- POST /auth/register - Register new user
- POST /auth/login - Login and receive JWT
- GET /auth/profile - Get user profile (authenticated)

## Tech Stack
- Framework: Sinatra
- Database: Sequel with PostgreSQL
- Authentication: JWT with jwt gem
```

Auto Code will:
- Detect Sinatra framework from `Gemfile`
- Generate handlers using Sinatra patterns
- Use proper error handling with custom error classes
- Include RSpec tests
- Follow Ruby security best practices
- Add helpers for JWT validation
- Use blocks and idiomatic Ruby patterns

---

## Additional Resources

- [Ruby Documentation](https://docs.ruby-lang.org/en/)
- [Ruby Style Guide](https://rubystyle.guide/)
- [Rails Guides](https://guides.rubyonrails.org/)
- [RSpec Documentation](https://rspec.info/documentation/)
- [Sinatra README](http://sinatrarb.com/intro.html)
- [bundler-audit](https://github.com/rubysec/bundler-audit)
- [Brakeman](https://brakemanscanner.org/)

---

**Need help?** Check the [Troubleshooting Guide](../../guides/TROUBLESHOOTING.md) or open an issue on GitHub.
