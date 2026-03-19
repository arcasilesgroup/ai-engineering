## Node.js Best Practices

### Project Structure

**Organize by feature:**

- Group related files together
- Separate routes, controllers, services, models
- Use `src/` for application code
- Keep configuration separate

**Pattern:**

```text
src/
  features/
    users/
      user.controller.js
      user.service.js
      user.model.js
      user.routes.js
    products/
      ...
  middleware/
  utils/
  config/
  app.js
  server.js
```text

### Async Patterns

**Always use async/await:**

- Never block the event loop
- Handle promise rejections
- Use async middleware
- Avoid callback hell

**Pattern:**

```javascript
// ✅ GOOD: Async/await
async function getUser(id) {
  try {
    const user = await User.findById(id);
    if (!user) {
      throw new NotFoundError('User not found');
    }
    return user;
  } catch (error) {
    logger.error('Error fetching user:', error);
    throw error;
  }
}

// ✅ GOOD: Async route handler
router.get('/users/:id', async (req, res, next) => {
  try {
    const user = await userService.getUser(req.params.id);
    res.json(user);
  } catch (error) {
    next(error);
  }
});

// ❌ BAD: Blocking operation
const data = fs.readFileSync('file.txt');  // Blocks event loop
```text

### Error Handling

**Centralized error handling:**

- Use error middleware
- Create custom error classes
- Always handle promise rejections
- Log errors properly

**Pattern:**

```javascript
// ✅ GOOD: Custom error classes
class NotFoundError extends Error {
  constructor(message) {
    super(message);
    this.name = 'NotFoundError';
    this.statusCode = 404;
  }
}

class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ValidationError';
    this.statusCode = 400;
  }
}

// ✅ GOOD: Error middleware
app.use((err, req, res, next) => {
  logger.error('Error:', {
    error: err.message,
    stack: err.stack,
    url: req.url,
  });

  const statusCode = err.statusCode || 500;
  res.status(statusCode).json({
    error: err.message,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  });
});

// ✅ GOOD: Unhandled rejection handler
process.on('unhandledRejection', (error) => {
  logger.error('Unhandled rejection:', error);
  process.exit(1);
});

process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception:', error);
  process.exit(1);
});
```text

### Express Best Practices

**RESTful API design:**

- Use router for routes
- Keep route handlers thin
- Use middleware for common tasks
- Validate input

**Pattern:**

```javascript
// ✅ GOOD: Router organization
// users.routes.js
import express from 'express';
import { authenticate } from '../middleware/auth.js';
import { validate } from '../middleware/validate.js';
import * as userController from './user.controller.js';
import { createUserSchema } from './user.validation.js';

const router = express.Router();

router.get('/', authenticate, userController.getUsers);
router.get('/:id', authenticate, userController.getUser);
router.post('/', authenticate, validate(createUserSchema), userController.createUser);
router.put('/:id', authenticate, userController.updateUser);
router.delete('/:id', authenticate, userController.deleteUser);

export default router;

// ✅ GOOD: Thin controller
// user.controller.js
export async function getUser(req, res, next) {
  try {
    const user = await userService.getUser(req.params.id);
    res.json(user);
  } catch (error) {
    next(error);
  }
}
```text

### Environment Configuration

**Use environment variables:**

- Never commit secrets
- Use dotenv for development
- Validate required config at startup
- Provide defaults when appropriate

**Pattern:**

```javascript
// ✅ GOOD: Configuration management
// config.js
import dotenv from 'dotenv';

dotenv.config();

const requiredEnvVars = ['DATABASE_URL', 'JWT_SECRET'];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
}

export const config = {
  port: process.env.PORT || 3000,
  nodeEnv: process.env.NODE_ENV || 'development',
  database: {
    url: process.env.DATABASE_URL,
  },
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRES_IN || '1d',
  },
};
```text

### Database Access

**Use connection pooling:**

- Don't create new connections per request
- Use async/await
- Handle connection errors
- Close connections gracefully

**Pattern:**

```javascript
// ✅ GOOD: Database connection
// db.js
import pg from 'pg';
import { config } from './config.js';

const pool = new pg.Pool({
  connectionString: config.database.url,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

pool.on('error', (err) => {
  logger.error('Unexpected database error:', err);
  process.exit(1);
});

export async function query(text, params) {
  const start = Date.now();
  try {
    const result = await pool.query(text, params);
    const duration = Date.now() - start;
    logger.debug('Executed query', { text, duration, rows: result.rowCount });
    return result;
  } catch (error) {
    logger.error('Query error:', { text, error });
    throw error;
  }
}

export async function close() {
  await pool.end();
}
```text

### Authentication & Authorization

**Secure your API:**

- Use JWT or sessions
- Hash passwords with bcrypt
- Validate tokens properly
- Implement role-based access

**Pattern:**

```javascript
// ✅ GOOD: Authentication middleware
import jwt from 'jsonwebtoken';
import { config } from '../config.js';

export function authenticate(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' });
  }

  const token = authHeader.substring(7);

  try {
    const decoded = jwt.verify(token, config.jwt.secret);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
}

export function authorize(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Not authenticated' });
    }

    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    next();
  };
}

// ✅ GOOD: Password hashing
import bcrypt from 'bcrypt';

export async function hashPassword(password) {
  const salt = await bcrypt.genSalt(10);
  return bcrypt.hash(password, salt);
}

export async function comparePassword(password, hash) {
  return bcrypt.compare(password, hash);
}
```text

### Logging

**Structured logging:**

- Use a logging library (winston, pino)
- Include context in logs
- Use appropriate log levels
- Don't log sensitive data

**Pattern:**

```javascript
// ✅ GOOD: Winston logger
import winston from 'winston';

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' }),
  ],
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple(),
  }));
}

export default logger;

// Usage
logger.info('User created', { userId: user.id });
logger.error('Database error', { error: err.message });
```text

### Validation

**Validate input:**

- Validate all user input
- Use validation library (joi, zod)
- Return clear error messages
- Sanitize input

**Pattern:**

```javascript
// ✅ GOOD: Joi validation
import Joi from 'joi';

export const createUserSchema = Joi.object({
  email: Joi.string().email().required(),
  name: Joi.string().min(3).max(50).required(),
  password: Joi.string().min(8).required(),
});

export function validate(schema) {
  return (req, res, next) => {
    const { error, value } = schema.validate(req.body, {
      abortEarly: false,
      stripUnknown: true,
    });

    if (error) {
      const errors = error.details.map(detail => ({
        field: detail.path.join('.'),
        message: detail.message,
      }));
      return res.status(400).json({ errors });
    }

    req.body = value;
    next();
  };
}
```text

### Graceful Shutdown

**Handle shutdown properly:**

- Close server gracefully
- Close database connections
- Finish in-flight requests
- Set timeout for forced shutdown

**Pattern:**

```javascript
// ✅ GOOD: Graceful shutdown
import http from 'http';
import app from './app.js';
import { close as closeDb } from './db.js';
import logger from './logger.js';

const server = http.createServer(app);
const port = process.env.PORT || 3000;

server.listen(port, () => {
  logger.info(`Server listening on port ${port}`);
});

async function shutdown(signal) {
  logger.info(`${signal} received, shutting down gracefully`);

  server.close(async () => {
    logger.info('HTTP server closed');

    try {
      await closeDb();
      logger.info('Database connections closed');
      process.exit(0);
    } catch (error) {
      logger.error('Error during shutdown:', error);
      process.exit(1);
    }
  });

  // Force shutdown after 10 seconds
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
```text

### Security

**Security best practices:**

- Use helmet for security headers
- Enable CORS properly
- Rate limit endpoints
- Sanitize input
- Use HTTPS in production

**Pattern:**

```javascript
// ✅ GOOD: Security setup
import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';

// Security headers
app.use(helmet());

// CORS
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
  credentials: true,
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests, please try again later',
});

app.use('/api/', limiter);
```text

### Testing

**Testing best practices:**

- Unit test services
- Integration test routes
- Mock external dependencies
- Use test database

**Pattern:**

```javascript
// ✅ GOOD: Unit test
import { describe, it, expect, vi } from 'vitest';
import { UserService } from './user.service.js';

describe('UserService', () => {
  it('should create user', async () => {
    const mockRepo = {
      create: vi.fn().mockResolvedValue({ id: '123', email: 'test@example.com' }),
    };

    const service = new UserService(mockRepo);
    const user = await service.createUser({ email: 'test@example.com' });

    expect(user.id).toBe('123');
    expect(mockRepo.create).toHaveBeenCalledWith({ email: 'test@example.com' });
  });
});

// ✅ GOOD: Integration test
import request from 'supertest';
import app from '../app.js';

describe('GET /api/users/:id', () => {
  it('should return user', async () => {
    const response = await request(app)
      .get('/api/users/123')
      .set('Authorization', 'Bearer valid-token');

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('id', '123');
  });
});
```text

### Common Anti-Patterns

**Avoid:**

- Synchronous file I/O in production
- Not handling promise rejections
- Blocking the event loop
- Putting business logic in routes
- Not using connection pooling
- Ignoring errors
- Memory leaks (event listeners, timers)
- Using `process.exit()` without cleanup
