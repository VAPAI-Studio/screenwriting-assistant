# frontend/Dockerfile

FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 4321

# Start the development server
CMD ["npm", "run", "dev", "--", "--host"]
