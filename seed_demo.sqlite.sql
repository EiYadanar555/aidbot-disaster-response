BEGIN;

-- Only volunteer (admin already exists from init_db)
INSERT INTO users (user_id, username, password_hash, role, first_name, last_name, email, phone, country, region, skills, avatar, bio, photo_path, deleted, created_at)
VALUES
  ('U-vol001','zarchi','password123','volunteer','Zarchi','Oo','zarchi@example.com','9826075','Myanmar','Bago','CPR,First Aid',NULL,'Volunteer',NULL,0,strftime('%s','now'));

-- Shelter
INSERT INTO shelters (shelter_id, name, region, country, latitude, longitude, capacity, available, contact, notes, created_at)
VALUES
  ('S-001','Yangon Shelter','Yangon','Myanmar',16.8409,96.1735,200,180,'+95-1-123456','Primary',strftime('%s','now'));

-- Resources
INSERT INTO resources (id, region, country, Volunteers, Trucks, Boats, MedKits, FoodKits, WaterKits)
VALUES
  ('R-001','Yangon','Myanmar',120,6,2,500,800,900);

-- Blood
INSERT INTO blood_inventory (id, region, country, blood_type, units, expires_on)
VALUES
  ('B-001','Yangon','Myanmar','O+',25,'2025-12-31');

-- Case
INSERT INTO cases (case_id, victim_name, contact_email, phone, region, country, latitude, longitude, description, attachment_path, status, assigned_to, shelter_id, timeline, created_at, acknowledged_at, arrived_at, closed_at)
VALUES
  ('C-0001','Ei Min','victim@example.com','0945000000','Yangon','Myanmar',16.84,96.17,'Needs help',NULL,'new','U-vol001','S-001','[]',strftime('%s','now'),NULL,NULL,NULL);

-- Form
INSERT INTO emergency_form (form_id, user_id, victim_name, contact_email, phone, region, country, latitude, longitude, description, attachment_path, case_id, submitted_at, status)
VALUES
  ('F-0001','U-vol001','Ei Min','victim@example.com','0945000000','Yangon','Myanmar',16.84,96.17,'Demo form',NULL,'C-0001',strftime('%s','now'),'converted');

-- Notification
INSERT INTO notifications (id, user_id, message, created_at, is_read)
VALUES
  ('N-001','U-vol001','You have been assigned to case C-0001',strftime('%s','now'),0);

-- Contact
INSERT INTO contact_messages (contact_id, name, email, message, submitted_at, status, responded_by, responded_at)
VALUES
  ('M-001','Test','test@example.com','Demo message',strftime('%s','now'),'new',NULL,NULL);

COMMIT;