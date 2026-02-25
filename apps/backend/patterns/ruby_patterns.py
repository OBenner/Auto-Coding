"""
Ruby Language Patterns Module
==============================

Idiomatic Ruby code patterns for code generation and analysis.
"""


# =============================================================================
# ERROR HANDLING PATTERNS
# =============================================================================

ERROR_HANDLING_PATTERNS = {
    "basic_rescue": """begin
  operation
rescue StandardError => e
  handle_error(e)
end""",
    "rescue_with_else": """begin
  operation
rescue StandardError => e
  handle_error(e)
else
  # runs if no exception
  success
ensure
  # always runs
  cleanup
end""",
    "inline_rescue": """result = risky_operation rescue default_value""",
    "custom_error": """class AppError < StandardError
  attr_reader :code, :details

  def initialize(message, code: 500, details: {})
    super(message)
    @code = code
    @details = details
  end
end

raise AppError.new("Not found", code: 404)""",
    "specific_rescue": """begin
  operation
rescue ArgumentError => e
  handle_argument_error(e)
rescue IOError => e
  handle_io_error(e)
rescue StandardError => e
  handle_generic_error(e)
end""",
    "retry_pattern": """attempts = 0
begin
  operation
rescue TransientError => e
  attempts += 1
  retry if attempts < 3
  raise
end""",
}


# =============================================================================
# OBJECT-ORIENTED PATTERNS
# =============================================================================

CLASS_PATTERNS = {
    "basic_class": """class User
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
end""",
    "inheritance": """class Animal
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
end""",
    "module_mixin": """module Loggable
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
end""",
    "singleton_pattern": """class Configuration
  include Singleton

  attr_accessor :host, :port

  def initialize
    @host = 'localhost'
    @port = 8080
  end
end

config = Configuration.instance""",
    "class_methods": """class User
  class << self
    def find(id)
      # class method implementation
    end

    def all
      # class method implementation
    end
  end

  # Or using self.
  def self.count
    # class method implementation
  end
end""",
    "struct_pattern": """User = Struct.new(:name, :email, :role) do
  def admin?
    role == 'admin'
  end
end

user = User.new('Alice', 'alice@example.com', 'admin')""",
}


# =============================================================================
# BLOCK AND ITERATOR PATTERNS
# =============================================================================

BLOCK_PATTERNS = {
    "basic_block": """[1, 2, 3].each do |num|
  puts num
end

# or
[1, 2, 3].each { |num| puts num }""",
    "yield_pattern": """def with_logging
  puts "Starting"
  result = yield
  puts "Finished"
  result
end

with_logging do
  puts "Working..."
  42
end""",
    "block_given": """def optional_block
  if block_given?
    yield
  else
    default_behavior
  end
end""",
    "proc_pattern": """greeter = Proc.new { |name| puts "Hello, #{name}!" }
greeter.call("Alice")

# Or stabby lambda syntax
greeter = ->(name) { puts "Hello, #{name}!" }
greeter.call("Bob")""",
    "lambda_pattern": """add = lambda { |a, b| a + b }
result = add.call(2, 3)

# Or stabby lambda
multiply = ->(a, b) { a * b }
result = multiply.call(2, 3)""",
    "map_select_reduce": """# Map
squared = [1, 2, 3].map { |n| n ** 2 }

# Select/Filter
evens = [1, 2, 3, 4].select { |n| n.even? }

# Reduce
sum = [1, 2, 3, 4].reduce(0) { |acc, n| acc + n }
# or
sum = [1, 2, 3, 4].reduce(:+)""",
    "method_as_block": """# Using symbol to proc
names = users.map(&:name)
uppercase = names.map(&:upcase)

# Using method reference
def double(x)
  x * 2
end

results = [1, 2, 3].map(&method(:double))""",
}


# =============================================================================
# METAPROGRAMMING PATTERNS
# =============================================================================

METAPROGRAMMING_PATTERNS = {
    "method_missing": """class DynamicAttributes
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
end""",
    "define_method": """class User
  ATTRIBUTES = [:name, :email, :role]

  ATTRIBUTES.each do |attr|
    define_method(attr) do
      instance_variable_get("@#{attr}")
    end

    define_method("#{attr}=") do |value|
      instance_variable_set("@#{attr}", value)
    end
  end
end""",
    "class_eval": """class User
  class_eval do
    def full_name
      "#{first_name} #{last_name}"
    end
  end
end""",
    "send_method": """object.send(:private_method)

# Dynamic method calls
method_name = :calculate
object.send(method_name, arg1, arg2)""",
    "class_attribute": """class Config
  class_attribute :setting

  self.setting = "default"
end

Config.setting = "production"
instance = Config.new
instance.setting # => "production\"""",
}


# =============================================================================
# TESTING PATTERNS
# =============================================================================

TESTING_PATTERNS = {
    "rspec_basic": """RSpec.describe Calculator do
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
end""",
    "rspec_context": """RSpec.describe User do
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
end""",
    "rspec_let": """RSpec.describe User do
  let(:user) { User.new(name: 'Alice', email: 'alice@example.com') }
  let(:admin) { User.new(name: 'Bob', email: 'bob@example.com', role: 'admin') }

  it 'has a name' do
    expect(user.name).to eq('Alice')
  end

  it 'can be an admin' do
    expect(admin).to be_admin
  end
end""",
    "rspec_before": """RSpec.describe Database do
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
end""",
    "minitest": """require 'minitest/autorun'

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
end""",
    "rspec_mock": """RSpec.describe UserService do
  it 'calls the mailer' do
    mailer = double('Mailer')
    expect(mailer).to receive(:send_welcome).with('alice@example.com')

    service = UserService.new(mailer: mailer)
    service.create_user(email: 'alice@example.com')
  end
end""",
}


# =============================================================================
# COLLECTION PATTERNS
# =============================================================================

COLLECTION_PATTERNS = {
    "array_operations": """# Create
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
arr.each_with_index { |x, i| puts "#{i}: #{x}" }""",
    "hash_operations": """# Create
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
hash.transform_values { |v| v.upcase }""",
    "enumerable_methods": """# Find
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

# Chunk
numbers.chunk(&:even?)""",
}


# =============================================================================
# STRING PATTERNS
# =============================================================================

STRING_PATTERNS = {
    "interpolation": """name = "Alice"
greeting = "Hello, #{name}!"

# Expression interpolation
result = "2 + 2 = #{2 + 2}\"""",
    "multiline_string": """# Heredoc
text = <<~TEXT
  This is a multiline string
  with indentation removed
TEXT

# With interpolation
message = <<~MSG
  Hello #{name},
  Welcome to the platform!
MSG""",
    "string_methods": """# Case
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
arr.join(', ')""",
    "symbols": """# Symbols are immutable strings
:symbol
:'symbol with spaces'

# Common use in hashes
options = {
  host: 'localhost',
  port: 8080,
  ssl: true
}""",
}


# =============================================================================
# FILE I/O PATTERNS
# =============================================================================

IO_PATTERNS = {
    "file_read": """# Read entire file
content = File.read('file.txt')

# Read lines
lines = File.readlines('file.txt')

# Block form (auto-closes)
File.open('file.txt', 'r') do |file|
  file.each_line do |line|
    puts line
  end
end""",
    "file_write": """# Write entire file
File.write('file.txt', content)

# Append
File.write('file.txt', content, mode: 'a')

# Block form
File.open('file.txt', 'w') do |file|
  file.puts "Line 1"
  file.puts "Line 2"
end""",
    "file_operations": """# Check existence
File.exist?('file.txt')
File.directory?('path')

# File info
File.size('file.txt')
File.mtime('file.txt')

# Path operations
File.join('path', 'to', 'file.txt')
File.basename('/path/to/file.txt')
File.dirname('/path/to/file.txt')
File.extname('file.txt')""",
    "dir_operations": """# List files
Dir.entries('.')
Dir.glob('*.rb')
Dir.glob('**/*.rb')  # recursive

# Create/Remove
Dir.mkdir('new_dir')
Dir.rmdir('old_dir')

# Iterate
Dir.foreach('.') do |file|
  puts file
end""",
}


# =============================================================================
# FRAMEWORK-SPECIFIC PATTERNS (RAILS)
# =============================================================================

RAILS_PATTERNS = {
    "rails_model": """class User < ApplicationRecord
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
end""",
    "rails_controller": """class UsersController < ApplicationController
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
end""",
    "rails_migration": """class CreateUsers < ActiveRecord::Migration[7.0]
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
end""",
    "rails_service": """class UserRegistrationService
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
end""",
    "rails_concern": """module Searchable
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
end""",
}


# =============================================================================
# FRAMEWORK-SPECIFIC PATTERNS (SINATRA)
# =============================================================================

SINATRA_PATTERNS = {
    "sinatra_basic": """require 'sinatra'

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
end""",
    "sinatra_modular": """require 'sinatra/base'

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
end""",
}


# =============================================================================
# COMBINED PATTERNS EXPORT
# =============================================================================

RUBY_PATTERNS = {
    "error_handling": ERROR_HANDLING_PATTERNS,
    "classes": CLASS_PATTERNS,
    "blocks": BLOCK_PATTERNS,
    "metaprogramming": METAPROGRAMMING_PATTERNS,
    "testing": TESTING_PATTERNS,
    "collections": COLLECTION_PATTERNS,
    "strings": STRING_PATTERNS,
    "io": IO_PATTERNS,
    "frameworks": {
        "rails": RAILS_PATTERNS,
        "sinatra": SINATRA_PATTERNS,
    },
}


__all__ = ["RUBY_PATTERNS"]
