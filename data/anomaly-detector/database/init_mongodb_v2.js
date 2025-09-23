// Script de inicialización para MongoDB V2
// Crear índices necesarios para optimizar consultas

// Conectar a la base de datos
use logsanomaly;

print("🚀 Inicializando MongoDB para arquitectura V2...");

// Crear colección de chunks si no existe
if (!db.chunks) {
    db.createCollection("chunks");
    print("✅ Colección 'chunks' creada");
}

// Crear colección de resultados si no existe
if (!db.results) {
    db.createCollection("results");
    print("✅ Colección 'results' creada");
}

// Crear índices para la colección chunks
print("📊 Creando índices para colección 'chunks'...");

// Índice compuesto para file_id y chunk_number
db.chunks.createIndex(
    { "file_id": 1, "chunk_number": 1 },
    { 
        name: "idx_file_chunk",
        background: true 
    }
);
print("✅ Índice 'idx_file_chunk' creado");

// Índice para processed
db.chunks.createIndex(
    { "processed": 1 },
    { 
        name: "idx_processed",
        background: true 
    }
);
print("✅ Índice 'idx_processed' creado");

// Índice para file_id
db.chunks.createIndex(
    { "file_id": 1 },
    { 
        name: "idx_file_id",
        background: true 
    }
);
print("✅ Índice 'idx_file_id' creado");

// Índice para created_at
db.chunks.createIndex(
    { "created_at": 1 },
    { 
        name: "idx_created_at",
        background: true 
    }
);
print("✅ Índice 'idx_created_at' creado");

// Crear índices para la colección results
print("📊 Creando índices para colección 'results'...");

// Índice para chunk_id
db.results.createIndex(
    { "chunk_id": 1 },
    { 
        name: "idx_chunk_id",
        background: true 
    }
);
print("✅ Índice 'idx_chunk_id' creado");

// Índice para created_at
db.results.createIndex(
    { "created_at": 1 },
    { 
        name: "idx_results_created_at",
        background: true 
    }
);
print("✅ Índice 'idx_results_created_at' creado");

// Índice de texto para búsquedas en anomalías
db.results.createIndex(
    { "anomalies.log_entry": "text", "anomalies.explanation": "text" },
    { 
        name: "idx_text_search",
        background: true 
    }
);
print("✅ Índice de texto 'idx_text_search' creado");

// Mostrar información de las colecciones
print("\n📋 Información de colecciones:");
print("Colecciones disponibles:", db.getCollectionNames());

print("\n📊 Índices de colección 'chunks':");
db.chunks.getIndexes().forEach(function(index) {
    print("- " + index.name + ": " + JSON.stringify(index.key));
});

print("\n📊 Índices de colección 'results':");
db.results.getIndexes().forEach(function(index) {
    print("- " + index.name + ": " + JSON.stringify(index.key));
});

// Insertar datos de prueba (opcional)
print("\n🧪 Insertando datos de prueba...");

// Datos de prueba para chunks
var testChunk = {
    file_id: "test-file-001",
    chunk_number: 0,
    data: "192.168.1.1 - - [25/Dec/2023:10:00:01 +0000] \"GET /api/users HTTP/1.1\" 200 1234\n192.168.1.2 - - [25/Dec/2023:10:00:02 +0000] \"POST /api/login HTTP/1.1\" 401 567",
    size: 150,
    processed: false,
    created_at: new Date()
};

db.chunks.insertOne(testChunk);
print("✅ Chunk de prueba insertado");

// Datos de prueba para results
var testResult = {
    chunk_id: testChunk._id.toString(),
    anomalies: [
        {
            log_entry: "192.168.1.2 - - [25/Dec/2023:10:00:02 +0000] \"POST /api/login HTTP/1.1\" 401 567",
            anomaly_score: -0.1,
            is_anomaly: true,
            explanation: "[ERROR_AUTENTICACIÓN] - Intento de login fallido",
            chunk_id: testChunk._id.toString()
        }
    ],
    processing_time: 0.5,
    created_at: new Date()
};

db.results.insertOne(testResult);
print("✅ Resultado de prueba insertado");

// Mostrar estadísticas
print("\n📈 Estadísticas:");
print("Total chunks:", db.chunks.countDocuments());
print("Total results:", db.results.countDocuments());
print("Chunks procesados:", db.chunks.countDocuments({ processed: true }));
print("Chunks pendientes:", db.chunks.countDocuments({ processed: false }));

print("\n🎉 Inicialización de MongoDB V2 completada!");
