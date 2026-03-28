-- ========================================
-- MySQL Database Setup Script
-- Knowledge Retention System (PS 1.1)
-- ========================================

-- Create database
CREATE DATABASE IF NOT EXISTS knowledge_retention_db;
USE knowledge_retention_db;

-- ========================================
-- USERS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  dailyGoal INT DEFAULT 10,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  isActive BOOLEAN DEFAULT TRUE,
  INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- TAKEAWAYS TABLE
-- (Main flashcard/takeaway storage)
-- ========================================
CREATE TABLE IF NOT EXISTS takeaways (
  id INT PRIMARY KEY AUTO_INCREMENT,
  userId INT NOT NULL,
  text TEXT NOT NULL,
  topic VARCHAR(100) NOT NULL,
  source VARCHAR(500),
  intervalDays INT DEFAULT 1,
  nextReview DATETIME NOT NULL,
  successCount INT DEFAULT 0,
  failureCount INT DEFAULT 0,
  reviewCount INT DEFAULT 0,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  lastReviewedAt DATETIME,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_userId_nextReview (userId, nextReview),
  INDEX idx_topic (topic),
  INDEX idx_nextReview (nextReview)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- REVIEW HISTORY TABLE
-- (For tracking individual review sessions)
-- ========================================
CREATE TABLE IF NOT EXISTS review_history (
  id INT PRIMARY KEY AUTO_INCREMENT,
  takeawayId INT NOT NULL,
  userId INT NOT NULL,
  remembered BOOLEAN NOT NULL,
  reviewedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (takeawayId) REFERENCES takeaways(id) ON DELETE CASCADE,
  FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_userId_reviewedAt (userId, reviewedAt),
  INDEX idx_takeawayId (takeawayId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- RETENTION STATS TABLE
-- (Aggregate retention scores by topic)
-- ========================================
CREATE TABLE IF NOT EXISTS retention_stats (
  id INT PRIMARY KEY AUTO_INCREMENT,
  userId INT NOT NULL,
  topic VARCHAR(100) NOT NULL,
  totalTakeaways INT DEFAULT 0,
  rememberedCount INT DEFAULT 0,
  totalReviews INT DEFAULT 0,
  retentionPercentage DECIMAL(5, 2) DEFAULT 0,
  lastUpdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY unique_user_topic (userId, topic),
  INDEX idx_userId (userId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- USER STATS TABLE
-- (Overall user statistics)
-- ========================================
CREATE TABLE IF NOT EXISTS user_stats (
  id INT PRIMARY KEY AUTO_INCREMENT,
  userId INT UNIQUE NOT NULL,
  totalTakeaways INT DEFAULT 0,
  totalReviews INT DEFAULT 0,
  totalRemembered INT DEFAULT 0,
  overallRetentionPercent DECIMAL(5, 2) DEFAULT 0,
  currentStreak INT DEFAULT 0,
  lastReviewDate DATE,
  lastUpdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- SAMPLE DATA
-- ========================================

-- Insert sample user
INSERT INTO users (name, email, password, dailyGoal, createdAt) 
VALUES (
  'John Learner',
  'john@example.com',
  '$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcg7b3XeKeUxWdeS86E36P4/KFm', -- 'password' hashed with bcrypt
  10,
  NOW()
);

-- Insert sample takeaways
INSERT INTO takeaways (userId, text, topic, source, intervalDays, nextReview, successCount, failureCount, reviewCount, createdAt, lastReviewedAt)
VALUES
(
  1,
  'The Ebbinghaus forgetting curve shows we forget ~50% of new info within 1 hour without review.',
  'Memory Science',
  'https://en.wikipedia.org/wiki/Forgetting_curve',
  1,
  DATE_ADD(NOW(), INTERVAL 1 DAY),
  3,
  1,
  4,
  NOW(),
  DATE_ADD(NOW(), INTERVAL -2 DAY)
),
(
  1,
  'Spaced repetition increases retention by 200% compared to massed practice.',
  'Learning Techniques',
  'https://www.learningscientists.org',
  3,
  DATE_ADD(NOW(), INTERVAL 3 DAY),
  5,
  0,
  5,
  NOW(),
  NOW()
),
(
  1,
  'Active recall is 5x more effective than passive rereading for long-term retention.',
  'Learning Techniques',
  'https://www.amazon.com/Make-Stick-Secrets-Successful-Learning/dp/0674729013',
  7,
  DATE_ADD(NOW(), INTERVAL 7 DAY),
  7,
  2,
  9,
  NOW(),
  NOW()
),
(
  1,
  'Sleep consolidates memories, increasing retention by up to 30% overnight.',
  'Sleep Science',
  'https://www.amazon.com/Why-We-Sleep-Unlocking-Dreams/dp/0374276234',
  14,
  DATE_ADD(NOW(), INTERVAL 14 DAY),
  4,
  0,
  4,
  NOW(),
  NOW()
),
(
  1,
  'Interleaving different topics while studying improves problem-solving by 20%.',
  'Learning Techniques',
  'https://www.psychologicalscience.org',
  30,
  DATE_ADD(NOW(), INTERVAL 30 DAY),
  2,
  1,
  3,
  NOW(),
  NOW()
);

-- Insert initial retention stats
INSERT INTO retention_stats (userId, topic, totalTakeaways, rememberedCount, totalReviews, retentionPercentage, lastUpdated)
VALUES
(1, 'Memory Science', 1, 3, 4, 75.00, NOW()),
(1, 'Learning Techniques', 3, 14, 17, 82.35, NOW()),
(1, 'Sleep Science', 1, 4, 4, 100.00, NOW());

-- Insert user stats
INSERT INTO user_stats (userId, totalTakeaways, totalReviews, totalRemembered, overallRetentionPercent, currentStreak, lastReviewDate, lastUpdated)
VALUES
(1, 5, 25, 21, 84.00, 3, CURDATE(), NOW());

-- ========================================
-- USEFUL QUERIES
-- ========================================

-- Get due takeaways for review
-- SELECT * FROM takeaways WHERE userId = 1 AND nextReview <= NOW() ORDER BY nextReview ASC;

-- Get retention stats by topic
-- SELECT * FROM retention_stats WHERE userId = 1 ORDER BY retentionPercentage DESC;

-- Get overall user retention
-- SELECT * FROM user_stats WHERE userId = 1;

-- Get recent review history
-- SELECT t.id, t.text, t.topic, rh.remembered, rh.reviewedAt 
-- FROM review_history rh 
-- JOIN takeaways t ON rh.takeawayId = t.id 
-- WHERE rh.userId = 1 
-- ORDER BY rh.reviewedAt DESC LIMIT 10;

-- Calculate retention percentage for a user
-- SELECT 
--   u.id, 
--   u.name,
--   COUNT(t.id) as totalTakeaways,
--   SUM(t.successCount) as totalRemembered,
--   SUM(t.reviewCount) as totalReviews,
--   ROUND((SUM(t.successCount) / SUM(t.reviewCount) * 100), 2) as retentionPercent
-- FROM users u
-- LEFT JOIN takeaways t ON u.id = t.userId
-- WHERE u.id = 1
-- GROUP BY u.id, u.name;