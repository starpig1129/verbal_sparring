FROM node:20-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source code
COPY . .

EXPOSE 5173

# Start Vite dev server exposing host for container mapping
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
