# Multi-stage Dockerfile for Auto Code Backend (CLI)
# Stage 1: Build stage with all dependencies
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage with minimal footprint
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy Python dependencies from builder stage to appuser's directory
COPY --from=builder /root/.local /home/appuser/.local

# Create directories for Auto Code data and set ownership
RUN mkdir -p /app/.auto-claude /app/.worktrees && \
    chown -R appuser:appuser /app /home/appuser/.local

# Switch to non-root user
USER appuser

# Add local Python packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Set Python to run in unbuffered mode for better logging in containers
ENV PYTHONUNBUFFERED=1

# Default command runs the CLI help
CMD ["python", "run.py", "--help"]
