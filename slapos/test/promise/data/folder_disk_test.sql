BEGIN TRANSACTION;
CREATE TABLE disk (partition text, used text, free text, mountpoint text,  date text, time text, reported integer NULL DEFAULT 0);
CREATE TABLE folder (partition text, disk_used real,  date text, time text, reported integer NULL DEFAULT 0);
INSERT INTO "disk" VALUES('/dev/vda2','159220666368','288948396032','/','2017-10-02','09:17:01',1);
INSERT INTO "disk" VALUES('/dev/vda2','159237537792','288931524608','/','2017-10-02','09:18:01',1);
INSERT INTO "disk" VALUES('/dev/vda2','159238090752','288930971648','/','2017-10-02','09:19:02',1);
INSERT INTO "disk" VALUES('/dev/vda2','159241568256','288927494144','/','2017-10-02','09:20:02',1);
INSERT INTO "disk" VALUES('/dev/vda2','159242719232','288926343168','/','2017-10-02','09:21:02',1);
INSERT INTO "disk" VALUES('/dev/vda2','159196176384','288972886016','/','2017-10-02','09:22:03',1);
INSERT INTO "disk" VALUES('/dev/vda2','159300747264','288868315136','/','2017-10-02','09:23:03',1);
INSERT INTO "disk" VALUES('/dev/vda2','159294308352','288874754048','/','2017-10-02','09:24:02',1);
INSERT INTO "disk" VALUES('/dev/vda2','159328468992','288840593408','/','2017-10-02','09:25:03',1);
INSERT INTO "disk" VALUES('/dev/vda2','159384883200','288784179200','/','2017-10-02','09:26:03',1);
INSERT INTO "disk" VALUES('/dev/vda2','159429677056','288739385344','/','2017-10-02','09:27:02',1);
INSERT INTO "disk" VALUES('/dev/vda2','159444549632','288724512768','/','2017-10-02','09:28:03',1);
INSERT INTO "disk" VALUES('/dev/vda2','159472902144','288696160256','/','2017-10-02','09:29:02',1);
INSERT INTO "disk" VALUES('/dev/vda2','159476805632','288692256768','/','2017-10-02','09:30:03',1);
INSERT INTO "folder" VALUES('slapuser0',21883255.0,'2017-09-18','09:30:20',1);
INSERT INTO "folder" VALUES('slapuser0',24071580.5,'2017-09-19','09:30:11',1);
INSERT INTO "folder" VALUES('slapuser0',23196250.3,'2017-09-20','09:30:08',1);
INSERT INTO "folder" VALUES('slapuser0',23415082.8,'2017-09-21','09:30:21',1);
INSERT INTO "folder" VALUES('slapuser0',23633915.4,'2017-09-22','09:30:09',1);
INSERT INTO "folder" VALUES('slapuser0',30636557.0,'2017-09-23','09:30:06',1);
INSERT INTO "folder" VALUES('slapuser0',28448231.5,'2017-09-24','09:30:19',1);
INSERT INTO "folder" VALUES('slapuser0',27572901.3,'2017-09-25','09:30:13',1);
INSERT INTO "folder" VALUES('slapuser0',29761226.8,'2017-09-26','09:30:15',1);
INSERT INTO "folder" VALUES('slapuser0',30855389.5,'2017-09-27','09:30:06',1);
INSERT INTO "folder" VALUES('slapuser0',30636557.0,'2017-09-28','09:30:11',1);
INSERT INTO "folder" VALUES('slapuser0',31074222.0,'2017-09-29','09:30:08',1);
INSERT INTO "folder" VALUES('slapuser0',31096105.3,'2017-09-30','09:30:05',1);
INSERT INTO "folder" VALUES('slapuser0',31949552.2,'2017-10-01','09:30:10',1);
INSERT INTO "folder" VALUES('slapuser0',87533020.0,'2017-10-02','09:30:02',1);
COMMIT;