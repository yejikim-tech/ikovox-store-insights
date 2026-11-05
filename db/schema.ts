// Intentionally empty by default.
// Add Drizzle tables here when the site actually needs a database.
// See examples/d1/db/schema.ts for an opt-in example.
import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';
export const costRecords=sqliteTable('cost_records',{id:text('id').primaryKey(),payload:text('payload').notNull(),revision:integer('revision').notNull(),updatedAt:text('updated_at').notNull()});
export const costHistory=sqliteTable('cost_history',{revision:integer('revision').primaryKey(),payload:text('payload').notNull(),updatedAt:text('updated_at').notNull()});
export const costLoginAttempts=sqliteTable('cost_login_attempts',{bucket:text('bucket').primaryKey(),attempts:integer('attempts').notNull()});
