FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

# Runs the Vite dev server bound to all interfaces so it is reachable
# from outside the container. For a production image, build a
# separate stage that runs `npm run build` and serves the static
# output instead (documented as a follow-up in the final report -
# this Dockerfile targets local/dev docker-compose usage, matching
# how the rest of this compose file runs the backend/worker).
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
