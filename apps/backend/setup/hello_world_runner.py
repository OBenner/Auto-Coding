import logging
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class HelloWorldTestResult(TypedDict):
    success: bool
    steps_completed: list[str]
    steps_failed: list[str]
    error_message: str | None
    summary: str


def run_hello_world_test() -> HelloWorldTestResult:
    steps_completed: list[str] = []
    steps_failed: list[str] = []
    error_message: str | None = None

    try:
        # Step 1: Verify Python version
        logger.info("Testing Python version...")
        try:
            if sys.version_info >= (3, 12, 0):
                steps_completed.append("Python version check")
                logger.debug("✓ Python version is sufficient")
            else:
                error_msg = f"Python {sys.version_info.major}.{sys.version_info.minor} is below required 3.12"
                steps_failed.append("Python version check")
                raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Python version check failed: {e}"
            steps_failed.append("Python version check")
            raise ValueError(error_msg)

        # Step 2: Test basic file operations
        logger.info("Testing file system operations...")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = Path(temp_dir) / "test.txt"
                test_file.write_text("Hello, Auto Code!")
                content = test_file.read_text()
                if content == "Hello, Auto Code!":
                    steps_completed.append("File system operations")
                    logger.debug("✓ File operations work correctly")
                else:
                    raise ValueError("File content mismatch")
        except Exception as e:
            error_msg = f"File system test failed: {e}"
            steps_failed.append("File system operations")
            raise ValueError(error_msg)

        # Step 3: Check environment setup
        logger.info("Testing environment setup...")
        try:
            env_file = Path(".env")
            if env_file.exists():
                steps_completed.append("Environment file exists")
                logger.debug("✓ .env file found")
            else:
                steps_failed.append("Environment file exists")
                raise ValueError(".env file not found")
        except Exception as e:
            error_msg = f"Environment check failed: {e}"
            steps_failed.append("Environment file check")
            raise ValueError(error_msg)

        # Step 4: Test core Python functionality
        logger.info("Testing core Python functionality...")
        try:
            test_math = 2 + 2 == 4
            test_string = "hello world".upper() == "HELLO WORLD"
            test_list = len([1, 2, 3]) == 3

            if test_math and test_string and test_list:
                steps_completed.append("Core Python functionality")
                logger.debug("✓ Core Python functionality works")
            else:
                raise ValueError("Basic Python operations failed")
        except Exception as e:
            error_msg = f"Core functionality test failed: {e}"
            steps_failed.append("Core Python functionality")
            raise ValueError(error_msg)

        summary = f"Setup verified successfully. {len(steps_completed)} tests passed."
        logger.info(summary)

        return {
            "success": True,
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "error_message": None,
            "summary": summary,
        }

    except Exception as e:
        error_message = str(e)
        summary = f"Setup verification failed: {error_message}"

        logger.error(summary)
        logger.debug("Failed steps: %s", steps_failed)

        return {
            "success": False,
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "error_message": error_message,
            "summary": summary,
        }
