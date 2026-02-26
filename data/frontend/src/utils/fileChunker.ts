export interface ChunkInfo {
  content: string;
  startLine: number;
  endLine: number;
  totalLines: number;
  chunkNumber: number;
  totalChunks: number;
  fileId: string;
  originalFileName: string;
}

function generateFileId(fileName: string, timestamp: number): string {
  // Combinar nombre de archivo y timestamp para crear un ID único
  const cleanFileName = fileName.replace(/[^a-zA-Z0-9]/g, '_');
  return `${cleanFileName}_${timestamp}`;
}

export async function splitLogFile(file: File, maxSizeInBytes: number = 512 * 1024): Promise<ChunkInfo[]> {  // 500KB
  const text = await file.text();
  const lines = text.split('\n');
  const chunks: ChunkInfo[] = [];
  
  // Generar ID único para este archivo
  const fileId = generateFileId(file.name, Date.now());
  
  let currentChunk = '';
  let currentSize = 0;
  let startLine = 0;
  let chunkNumber = 0;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] + '\n';
    const lineSize = new Blob([line]).size;
    
    // Si la línea por sí sola excede el tamaño máximo, la dividimos
    if (lineSize > maxSizeInBytes) {
      const parts = Math.ceil(lineSize / maxSizeInBytes);
      for (let j = 0; j < parts; j++) {
        const start = j * maxSizeInBytes;
        const end = Math.min((j + 1) * maxSizeInBytes, line.length);
        const part = line.slice(start, end);
        
        chunks.push({
          content: part,
          startLine: i,
          endLine: i,
          totalLines: lines.length,
          chunkNumber: chunkNumber++,
          totalChunks: -1, // Se actualizará al final
          fileId,
          originalFileName: file.name
        });
      }
      startLine = i + 1;
      currentChunk = '';
      currentSize = 0;
      continue;
    }
    
    // Si agregar la siguiente línea excede el tamaño máximo, creamos un nuevo chunk
    if (currentSize + lineSize > maxSizeInBytes && currentChunk !== '') {
      chunks.push({
        content: currentChunk,
        startLine,
        endLine: i - 1,
        totalLines: lines.length,
        chunkNumber: chunkNumber++,
        totalChunks: -1,
        fileId,
        originalFileName: file.name
      });
      startLine = i;
      currentChunk = '';
      currentSize = 0;
    }
    
    currentChunk += line;
    currentSize += lineSize;
  }
  
  // Agregar el último chunk si existe
  if (currentChunk !== '') {
    chunks.push({
      content: currentChunk,
      startLine,
      endLine: lines.length - 1,
      totalLines: lines.length,
      chunkNumber: chunkNumber++,
      totalChunks: -1,
      fileId,
      originalFileName: file.name
    });
  }
  
  // Actualizar el número total de chunks
  chunks.forEach(chunk => {
    chunk.totalChunks = chunks.length;
  });
  
  return chunks;
}

export function createChunkFile(chunk: ChunkInfo): File {
  const metadata = {
    startLine: chunk.startLine,
    endLine: chunk.endLine,
    totalLines: chunk.totalLines,
    chunkNumber: chunk.chunkNumber,
    totalChunks: chunk.totalChunks
  };
  
  // Crear el archivo solo con el contenido del chunk
  const fileName = `${chunk.fileId}_chunk${chunk.chunkNumber + 1}of${chunk.totalChunks}.txt`;
  
  return new File(
    [chunk.content],
    fileName,
    { 
      type: 'text/plain',
      lastModified: Date.now()
    }
  );
}
