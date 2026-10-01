FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install express
COPY . .
EXPOSE 3000
# CMD ["npm", "run", "dev"]
CMD ["node", "src/app.js"]