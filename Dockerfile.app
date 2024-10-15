# Use the official slim Python image from the Docker Hub
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install sudo
RUN apt-get update && \
    apt-get install -y sudo git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a new user called tawjeeh with sudo privileges
RUN useradd -m -s /bin/bash tawjeeh && \
    echo "tawjeeh ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to the tawjeeh user
USER tawjeeh

# Set the working directory
WORKDIR /app

# Create a virtual environment
RUN python -m venv venv

# Copy the current directory contents into the container at /app
COPY --chown=tawjeeh:tawjeeh . /app

# Activate the virtual environment and install the requirements
RUN /bin/bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Run the app
CMD ["bash", "deploy.sh"]
