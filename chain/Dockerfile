FROM node:22-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Expose Hardhat RPC port
EXPOSE 8545

# Start Hardhat node bound to all interfaces so other containers can reach it
CMD ["npx", "hardhat", "node", "--hostname", "0.0.0.0"]
