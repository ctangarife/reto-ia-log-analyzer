// Crear base de datos y colecciones
db = db.getSiblingDB('logsanomaly');

// Crear colecciones con validación de esquema
db.createCollection("chunks", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["file_id", "chunk_number", "data", "size", "processed"],
            properties: {
                file_id: { bsonType: "string" },
                chunk_number: { bsonType: "int" },
                data: { bsonType: "string" },
                size: { bsonType: "int" },
                processed: { bsonType: "bool" },
                created_at: { bsonType: "date" }
            }
        }
    }
});

db.createCollection("results", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["chunk_id", "anomalies"],
            properties: {
                chunk_id: { bsonType: "string" },
                anomalies: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        required: ["log_entry", "score", "explanation"],
                        properties: {
                            log_entry: { bsonType: "string" },
                            score: { bsonType: "double" },
                            explanation: { bsonType: "string" }
                        }
                    }
                },
                processing_time: { bsonType: "double" },
                created_at: { bsonType: "date" }
            }
        }
    }
});

// Crear índices
db.chunks.createIndex({ "file_id": 1, "chunk_number": 1 }, { unique: true });
db.chunks.createIndex({ "processed": 1 });
db.chunks.createIndex({ "created_at": 1 });

db.results.createIndex({ "chunk_id": 1 });
db.results.createIndex({ "created_at": 1 });
db.results.createIndex({ "anomalies.score": 1 });
