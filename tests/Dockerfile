FROM python:3.11-slim

WORKDIR /tests

# Install pytest and any other dependencies
RUN pip install --no-cache-dir pytest
RUN pip install --no-cache-dir pytest-depends
RUN pip install --no-cache-dir requests

# Copy tests and optionally source code if needed for imports
COPY test_*.py .

# Set default command to run pytest
CMD ["pytest"]