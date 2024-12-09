FROM python:3.12-slim  
  
# Set the working directory  
WORKDIR /app  
  
# Copy requirements and install them  
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt  
  
# Copy the application code  
COPY *.py .  
COPY gbb /app/gbb
COPY sk /app/sk
  
# Expose the port  
EXPOSE 8000 
  
# Command to run the application  
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]  