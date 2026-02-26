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

// Crear índices para optimizar consultas
print("📊 Creando índices...");

// Índices para colección chunks
db.chunks.createIndex(
    { "file_id": 1, "chunk_number": 1 }, 
    { 
        unique: true,
        name: "idx_file_chunk",
        background: true 
    }
);
print("✅ Índice 'idx_file_chunk' creado");

db.chunks.createIndex(
    { "file_id": 1 },
    { 
        name: "idx_file_id",
        background: true 
    }
);
print("✅ Índice 'idx_file_id' creado");

db.chunks.createIndex(
    { "processed": 1 },
    { 
        name: "idx_processed",
        background: true 
    }
);
print("✅ Índice 'idx_processed' creado");

db.chunks.createIndex(
    { "created_at": 1 },
    { 
        name: "idx_created_at",
        background: true 
    }
);
print("✅ Índice 'idx_created_at' creado");

// Índices para colección results
db.results.createIndex(
    { "chunk_id": 1 },
    { 
        name: "idx_chunk_id",
        background: true 
    }
);
print("✅ Índice 'idx_chunk_id' creado");

db.results.createIndex(
    { "created_at": 1 },
    { 
        name: "idx_results_created_at",
        background: true 
    }
);
print("✅ Índice 'idx_results_created_at' creado");

db.results.createIndex(
    { "anomalies.score": 1 },
    { 
        name: "idx_anomaly_score",
        background: true 
    }
);
print("✅ Índice 'idx_anomaly_score' creado");

// Índice de texto para búsquedas en anomalías (opcional, puede ser pesado)
try {
    db.results.createIndex(
        { "anomalies.log_entry": "text", "anomalies.explanation": "text" },
        { 
            name: "idx_text_search",
            background: true 
        }
    );
    print("✅ Índice de texto 'idx_text_search' creado");
} catch (e) {
    print("⚠️ Índice de texto no creado (puede requerir configuración adicional)");
}

print("🎉 Inicialización de MongoDB completada!");
