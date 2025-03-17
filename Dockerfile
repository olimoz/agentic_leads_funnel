# Use an official Python runtime as a base image
FROM python:3.10.14

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set up environment variables
ENV AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=webresearchapp;AccountKey=;EndpointSuffix=core.windows.net"
ENV AZURE_CONTAINER_NAME=webresearchapp
ENV ENVIRONMENT=PROD

COPY . .

# Make app.py executable
RUN chmod +x app.py

# Set the default command
CMD ["python", "app.py"]
