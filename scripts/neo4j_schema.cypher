// Idempotent — safe to re-run.

CREATE CONSTRAINT person_id   IF NOT EXISTS FOR (p:Person)   REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT party_id    IF NOT EXISTS FOR (p:Party)    REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT bill_id     IF NOT EXISTS FOR (b:Bill)     REQUIRE b.id IS UNIQUE;
CREATE CONSTRAINT congress_id IF NOT EXISTS FOR (c:Congress) REQUIRE c.id IS UNIQUE;

CREATE INDEX person_name  IF NOT EXISTS FOR (p:Person) ON (p.full_name);
CREATE INDEX bill_no      IF NOT EXISTS FOR (b:Bill)   ON (b.bill_no);
CREATE INDEX bill_status  IF NOT EXISTS FOR (b:Bill)   ON (b.status);

// Relationship types:
// (Person)-[:SPONSORED  {sequence_no, role: "author"}]->(Bill)
// (Person)-[:CO_SPONSORED {journal_no, date}]->(Bill)
// (Person)-[:VOTED      {result, stage, date}]->(Bill)
// (Person)-[:MEMBER_OF  {congress_id}]->(Party)
// (Person)-[:SERVED_IN  {chamber}]->(Congress)
