// ========================================
// Backend Server for Knowledge Retention System
// Express.js with MySQL
// ========================================

require('dotenv').config();
const express = require('express');
const mysql = require('mysql2/promise');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const cors = require('cors');

// Initialize Express app
const app = express();

// Middleware
app.use(express.json());
app.use(cors());

// ========================================
// MYSQL CONNECTION
// ========================================
let db;

async function initializeDatabase() {
  try {
    db = await mysql.createConnection({
      host: process.env.DB_HOST || 'localhost',
      user: process.env.DB_USER || 'root',
      password: process.env.DB_PASSWORD || '',
      database: process.env.DB_NAME || 'knowledge_retention_db',
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0
    });

    console.log('✅ MySQL connected');
  } catch (err) {
    console.log('❌ MySQL connection error:', err);
    process.exit(1);
  }
}

// Initialize database connection
initializeDatabase();
  source: String,
  intervalDays: { type: Number, default: 1 },
  nextReview: { type: Date, required: true },
  successCount: { type: Number, default: 0 },
// ========================================
// HELPER FUNCTIONS
// ========================================

// JWT Token Generation
function generateToken(userId) {
  return jwt.sign({ userId }, process.env.JWT_SECRET || 'your_secret_key', { expiresIn: '7d' });
}

// Middleware to verify JWT token
async function verifyToken(req, res, next) {
  const token = req.headers['authorization']?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'your_secret_key');
    req.userId = decoded.userId;
    next();
  } catch (err) {
    res.status(401).json({ error: 'Invalid token' });
  }
}

// Calculate next review date based on spaced repetition intervals
function calculateNextReview(reviewCount) {
  const intervals = [1, 3, 7, 14, 30]; // days
  const interval = intervals[Math.min(reviewCount, intervals.length - 1)];
  const nextDate = new Date();
  nextDate.setDate(nextDate.getDate() + interval);
  return nextDate;
}

// Recalculate retention statistics for a user
async function updateRetentionStats(userId, topic) {
  try {
    // Get all takeaways for this user and topic
    const [takeaways] = await db.execute(
      'SELECT * FROM takeaways WHERE userId = ? AND topic = ?',
      [userId, topic]
    );

    if (takeaways.length === 0) {
      await db.execute('DELETE FROM retention_stats WHERE userId = ? AND topic = ?', [userId, topic]);
      return;
    }

    const totalTakeaways = takeaways.length;
    const rememberedCount = takeaways.reduce((sum, t) => sum + t.successCount, 0);
    const totalReviews = takeaways.reduce((sum, t) => sum + t.reviewCount, 0);
    const retentionPercentage = totalReviews > 0 ? Math.round((rememberedCount / totalReviews) * 100) : 0;

    await db.execute(
      `INSERT INTO retention_stats (userId, topic, totalTakeaways, rememberedCount, totalReviews, retentionPercentage, lastUpdated)
       VALUES (?, ?, ?, ?, ?, ?, NOW())
       ON DUPLICATE KEY UPDATE
       totalTakeaways = VALUES(totalTakeaways),
       rememberedCount = VALUES(rememberedCount),
       totalReviews = VALUES(totalReviews),
       retentionPercentage = VALUES(retentionPercentage),
       lastUpdated = NOW()`,
      [userId, topic, totalTakeaways, rememberedCount, totalReviews, retentionPercentage]
    );
  } catch (err) {
    console.error('Error updating retention stats:', err);
  }
}

// ========================================
// AUTHENTICATION ROUTES
// ========================================

// Register
app.post('/api/auth/register', async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Check if user already exists
    const [existingUsers] = await db.execute('SELECT id FROM users WHERE email = ?', [email]);
    if (existingUsers.length > 0) {
      return res.status(400).json({ error: 'Email already registered' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);

    // Insert new user
    const [result] = await db.execute(
      'INSERT INTO users (name, email, password, dailyGoal, createdAt) VALUES (?, ?, ?, 10, NOW())',
      [name, email, hashedPassword]
    );

    const userId = result.insertId;
    const token = generateToken(userId);

    res.status(201).json({
      message: 'User registered successfully',
      userId,
      token
    });
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Login
app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password required' });
    }

    // Find user by email
    const [users] = await db.execute('SELECT * FROM users WHERE email = ?', [email]);
    if (users.length === 0) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    const user = users[0];
    const isPasswordValid = await bcrypt.compare(password, user.password);
    if (!isPasswordValid) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    const token = generateToken(user.id);
    res.json({
      message: 'Login successful',
      userId: user.id,
      token
    });
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});
});

// Login
app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password required' });
    }

// ========================================
// TAKEAWAY CRUD ROUTES
// ========================================

// Get all takeaways for user
app.get('/api/takeaways', verifyToken, async (req, res) => {
  try {
    const [takeaways] = await db.execute(
      'SELECT * FROM takeaways WHERE userId = ? ORDER BY nextReview ASC',
      [req.userId]
    );
    res.json(takeaways);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Get due takeaways (for review)
app.get('/api/takeaways/due', verifyToken, async (req, res) => {
  try {
    const [dueTakeaways] = await db.execute(
      'SELECT * FROM takeaways WHERE userId = ? AND nextReview <= NOW() ORDER BY nextReview ASC',
      [req.userId]
    );
    res.json(dueTakeaways);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Get single takeaway
app.get('/api/takeaways/:id', verifyToken, async (req, res) => {
  try {
    const [takeaways] = await db.execute(
      'SELECT * FROM takeaways WHERE id = ? AND userId = ?',
      [req.params.id, req.userId]
    );

    if (takeaways.length === 0) {
      return res.status(404).json({ error: 'Takeaway not found' });
    }

    res.json(takeaways[0]);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Create new takeaway
app.post('/api/takeaways', verifyToken, async (req, res) => {
  try {
    const { text, topic, source } = req.body;

    if (!text || !topic) {
      return res.status(400).json({ error: 'Text and topic required' });
    }

    const nextReview = new Date();
    nextReview.setDate(nextReview.getDate() + 1); // First review in 1 day

    const [result] = await db.execute(
      `INSERT INTO takeaways (userId, text, topic, source, intervalDays, nextReview, successCount, failureCount, reviewCount, createdAt)
       VALUES (?, ?, ?, ?, 1, ?, 0, 0, 0, NOW())`,
      [req.userId, text, topic, source || null, nextReview]
    );

    const takeawayId = result.insertId;
    await updateRetentionStats(req.userId, topic);

    // Get the created takeaway
    const [takeaways] = await db.execute('SELECT * FROM takeaways WHERE id = ?', [takeawayId]);

    res.status(201).json(takeaways[0]);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Update takeaway
app.put('/api/takeaways/:id', verifyToken, async (req, res) => {
  try {
    const { text, topic, source } = req.body;

    const [result] = await db.execute(
      'UPDATE takeaways SET text = ?, topic = ?, source = ?, updatedAt = NOW() WHERE id = ? AND userId = ?',
      [text, topic, source || null, req.params.id, req.userId]
    );

    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Takeaway not found' });
    }

    await updateRetentionStats(req.userId, topic);

    // Get updated takeaway
    const [takeaways] = await db.execute('SELECT * FROM takeaways WHERE id = ?', [req.params.id]);

    res.json(takeaways[0]);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Delete takeaway
app.delete('/api/takeaways/:id', verifyToken, async (req, res) => {
  try {
    // Get topic before deleting
    const [takeaways] = await db.execute('SELECT topic FROM takeaways WHERE id = ? AND userId = ?', [req.params.id, req.userId]);
    const topic = takeaways.length > 0 ? takeaways[0].topic : null;

    const [result] = await db.execute('DELETE FROM takeaways WHERE id = ? AND userId = ?', [req.params.id, req.userId]);

    if (result.affectedRows === 0) {
      return res.status(404).json({ error: 'Takeaway not found' });
    }

    if (topic) {
      await updateRetentionStats(req.userId, topic);
    }

// ========================================
// REVIEW ROUTES
// ========================================

// Mark takeaway as remembered or forgot
app.post('/api/takeaways/:id/review', verifyToken, async (req, res) => {
  try {
    const { remembered } = req.body;

    // Get current takeaway
    const [takeaways] = await db.execute('SELECT * FROM takeaways WHERE id = ? AND userId = ?', [req.params.id, req.userId]);

    if (takeaways.length === 0) {
      return res.status(404).json({ error: 'Takeaway not found' });
    }

    const takeaway = takeaways[0];

    // Update counts
    const newReviewCount = takeaway.reviewCount + 1;
    const newSuccessCount = remembered ? takeaway.successCount + 1 : takeaway.successCount;
    const newFailureCount = remembered ? takeaway.failureCount : takeaway.failureCount + 1;

    // Calculate next review
    const nextReview = calculateNextReview(newReviewCount);
    const intervalDays = Math.ceil((nextReview - new Date()) / (1000 * 60 * 60 * 24));

    // Update takeaway
    await db.execute(
      `UPDATE takeaways SET
       successCount = ?, failureCount = ?, reviewCount = ?,
       nextReview = ?, intervalDays = ?, lastReviewedAt = NOW(), updatedAt = NOW()
       WHERE id = ? AND userId = ?`,
      [newSuccessCount, newFailureCount, newReviewCount, nextReview, intervalDays, req.params.id, req.userId]
    );

    // Insert review history
    await db.execute(
      'INSERT INTO review_history (takeawayId, userId, remembered, reviewedAt) VALUES (?, ?, ?, NOW())',
      [req.params.id, req.userId, remembered]
    );

    // Update retention stats
    await updateRetentionStats(req.userId, takeaway.topic);

    // Get updated takeaway
    const [updatedTakeaways] = await db.execute('SELECT * FROM takeaways WHERE id = ?', [req.params.id]);

    res.json({
      message: 'Review recorded',
      takeaway: updatedTakeaways[0]
    });
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// ========================================
// RETENTION STATS ROUTES
// ========================================

// Get overall retention score
app.get('/api/retention/score', verifyToken, async (req, res) => {
  try {
    const takeaways = await Takeaway.find({ userId: req.userId });

    const totalRemembered = takeaways.reduce((sum, t) => sum + t.successCount, 0);
    const totalReviews = takeaways.reduce((sum, t) => sum + t.reviewCount, 0);
    const overallPercentage = totalReviews > 0 ? Math.round((totalRemembered / totalReviews) * 100) : 0;

    res.json({
      totalTakeaways: takeaways.length,
      totalRemembered,
      totalReviews,
      overallPercentage
    });
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Get retention stats by topic
app.get('/api/retention/by-topic', verifyToken, async (req, res) => {
  try {
    const [stats] = await db.execute(
      'SELECT * FROM retention_stats WHERE userId = ? ORDER BY retentionPercentage DESC',
      [req.userId]
    );

    res.json(stats);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// ========================================
// RETENTION STATS ROUTES
// ========================================

// Get overall retention score
app.get('/api/retention/score', verifyToken, async (req, res) => {
  try {
    const [takeaways] = await db.execute('SELECT * FROM takeaways WHERE userId = ?', [req.userId]);

    const totalRemembered = takeaways.reduce((sum, t) => sum + t.successCount, 0);
    const totalReviews = takeaways.reduce((sum, t) => sum + t.reviewCount, 0);
    const overallPercentage = totalReviews > 0 ? Math.round((totalRemembered / totalReviews) * 100) : 0;

    res.json({
      totalTakeaways: takeaways.length,
      totalRemembered,
      totalReviews,
      overallPercentage
    });
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Get retention stats by topic
app.get('/api/retention/by-topic', verifyToken, async (req, res) => {
  try {
    const [stats] = await db.execute(
      'SELECT * FROM retention_stats WHERE userId = ? ORDER BY retentionPercentage DESC',
      [req.userId]
    );

    res.json(stats);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// ========================================
// SEARCH ROUTES
// ========================================

// Search takeaways by keyword
app.get('/api/search', verifyToken, async (req, res) => {
  try {
    const { q } = req.query;

    if (!q) {
      return res.status(400).json({ error: 'Search query required' });
    }

    const [takeaways] = await db.execute(
      `SELECT * FROM takeaways WHERE userId = ? AND
       (text LIKE ? OR topic LIKE ? OR source LIKE ?)`,
      [req.userId, `%${q}%`, `%${q}%`, `%${q}%`]
    );

    res.json(takeaways);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// ========================================
// ANALYTICS ROUTES
// ========================================

// Get review history
app.get('/api/analytics/history', verifyToken, async (req, res) => {
  try {
    const { limit = 50 } = req.query;

    const [history] = await db.execute(
      `SELECT rh.*, t.text, t.topic
       FROM review_history rh
       JOIN takeaways t ON rh.takeawayId = t.id
       WHERE rh.userId = ?
       ORDER BY rh.reviewedAt DESC
       LIMIT ?`,
      [req.userId, parseInt(limit)]
    );

    res.json(history);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// Get statistics
app.get('/api/analytics/stats', verifyToken, async (req, res) => {
  try {
    // Get total takeaways
    const [takeawayResult] = await db.execute('SELECT COUNT(*) as count FROM takeaways WHERE userId = ?', [req.userId]);
    const totalTakeaways = takeawayResult[0].count;

    // Get total reviews
    const [reviewResult] = await db.execute('SELECT COUNT(*) as count FROM review_history WHERE userId = ?', [req.userId]);
    const totalReviews = reviewResult[0].count;

    // Get unique topics
    const [topicResult] = await db.execute('SELECT COUNT(DISTINCT topic) as count FROM takeaways WHERE userId = ?', [req.userId]);
    const topics = topicResult[0].count;

    // Get average success rate
    const [successResult] = await db.execute(
      'SELECT AVG(CASE WHEN remembered = 1 THEN 1 ELSE 0 END) * 100 as rate FROM review_history WHERE userId = ?',
      [req.userId]
    );
    const averageSuccessRate = Math.round(successResult[0].rate || 0);

    const stats = {
      totalTakeaways,
      totalReviews,
      topics,
      averageSuccessRate
    };

    res.json(stats);
  } catch (err) {
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// ========================================
// START SERVER
// ========================================
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✅ Server running on http://localhost:${PORT}`);
  console.log(`📚 API docs:`);
  console.log(`   POST   /api/auth/register`);
  console.log(`   POST   /api/auth/login`);
  console.log(`   GET    /api/takeaways`);
  console.log(`   POST   /api/takeaways`);
  console.log(`   GET    /api/takeaways/:id`);
  console.log(`   PUT    /api/takeaways/:id`);
  console.log(`   DELETE /api/takeaways/:id`);
  console.log(`   POST   /api/takeaways/:id/review`);
  console.log(`   GET    /api/retention/score`);
  console.log(`   GET    /api/retention/by-topic`);
  console.log(`   GET    /api/search?q=keyword`);
  console.log(`   GET    /api/analytics/history`);
  console.log(`   GET    /api/analytics/stats`);
});

module.exports = app;