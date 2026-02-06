from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional
import uvicorn
import uuid
import time

app = FastAPI()


class ConnectionInfo(BaseModel):
    connectionUrl: str


class QueryRequest(BaseModel):
    sql: str
    connectionInfo: ConnectionInfo


class QueryResponse(BaseModel):
    columns: List[str]
    data: List[List[Any]]
    dtypes: Dict[str, str]


@app.post("/v3/connector/postgres/query", response_model=QueryResponse)
async def query_postgres(request: QueryRequest, response: Response, dryRun: bool = False, truncate: bool = True):
    """
    Execute SQL query on PostgreSQL/PostGIS database
    
    Args:
        request: QueryRequest containing SQL query and connection info
        dryRun: If True, only validate SQL syntax without fetching data
        truncate: If True, truncate geodata values to avoid excessive length (default: True)
        
    Returns:
        QueryResponse with columns, data, and dtypes
    """
    # Generate correlation ID and start timing
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    
    engine = None
    try:
        # Create database engine
        engine = create_engine(request.connectionInfo.connectionUrl)
        print("Request SQL:", request.sql)
        # Execute query
        with engine.connect() as connection:
            result = connection.execute(text(request.sql))
            
            # If dryRun, just validate and return empty response
            if dryRun:
                # Calculate process time and set response headers
                process_time = time.time() - start_time
                response.headers['x-correlation-id'] = correlation_id
                response.headers['x-process-time'] = str(process_time)
                response.headers['x-cache-hit'] = 'false'
                
                return QueryResponse(
                    columns=[],
                    data=[],
                    dtypes={}
                )
            
            # Get column names
            columns = list(result.keys())
            
            # Get column types from cursor description BEFORE fetching data
            dtypes = {}
            if result.cursor and result.cursor.description:
                # Extract OIDs from cursor description
                oids = [desc[1] for desc in result.cursor.description]
                
                # Query pg_type to get type names
                type_query = text(f"SELECT oid, typname FROM pg_type WHERE oid IN ({','.join(map(str, oids))})")
                type_result = connection.execute(type_query)
                oid_to_typename = {row[0]: row[1] for row in type_result.fetchall()}
                
                # Map type names to our data type strings
                for i, col_name in enumerate(columns):
                    oid = result.cursor.description[i][1]
                    typename = oid_to_typename.get(oid, 'unknown')
                    
                    # Map PostgreSQL type names to our type strings
                    if typename in ['int2', 'int4', 'int8', 'serial', 'bigserial']:
                        dtypes[col_name] = 'int64'
                    elif typename in ['float4', 'float8', 'numeric', 'decimal', 'real', 'double precision']:
                        dtypes[col_name] = 'float64'
                    elif typename == 'bool':
                        dtypes[col_name] = 'bool'
                    elif typename in ['date', 'time', 'timestamp', 'timestamptz', 'timetz']:
                        dtypes[col_name] = 'datetime'
                    elif typename in ['char', 'varchar', 'text', 'bpchar']:
                        dtypes[col_name] = 'string'
                    else:
                        dtypes[col_name] = typename
            
            # Fetch all rows (cursor becomes None after this)
            rows = result.fetchall()
            data = [list(row) for row in rows]
            
            # Truncate geodata if needed
            if truncate:
                geo_column_indices = []
                for i, col_name in enumerate(columns):
                    typename = dtypes.get(col_name, '')
                    # Check if column is a geometry/geography type
                    if typename and ('geometry' in typename.lower() or 'geography' in typename.lower()):
                        geo_column_indices.append(i)
                
                # Truncate geometry/geography values in data
                if geo_column_indices:
                    for row in data:
                        for idx in geo_column_indices:
                            if row[idx] is not None and isinstance(row[idx], str) and len(row[idx]) > 100:
                                row[idx] = row[idx][:97] + '...'
            
            # Fallback: if dtypes is empty, infer from actual data
            if not dtypes:
                for i, col_name in enumerate(columns):
                    col_type = None
                    for row in data:
                        if row[i] is not None:
                            col_type = type(row[i])
                            break
                    
                    if col_type is None:
                        dtypes[col_name] = 'string'
                    elif col_type in (int,):
                        dtypes[col_name] = 'int64'
                    elif col_type in (float,):
                        dtypes[col_name] = 'float64'
                    elif col_type in (bool,):
                        dtypes[col_name] = 'bool'
                    elif col_type.__name__ in ('datetime', 'date', 'time'):
                        dtypes[col_name] = 'datetime'
                    elif hasattr(col_type, '__mro__') and any('geometry' in str(c).lower() or 'geography' in str(c).lower() for c in col_type.__mro__):
                        dtypes[col_name] = 'geometry'
                    else:
                        dtypes[col_name] = 'string'
            
            # Calculate process time and set response headers
            process_time = time.time() - start_time
            response.headers['x-correlation-id'] = correlation_id
            response.headers['x-process-time'] = str(process_time)
            response.headers['x-cache-hit'] = 'false'
            
            return QueryResponse(
                columns=columns,
                data=data,
                dtypes=dtypes
            )
    except SQLAlchemyError as e:
        return PlainTextResponse(
            status_code=500,
            content=f"SQLAlchemy error: {e}"
        )
    except Exception as e:
        return PlainTextResponse(
            status_code=500,
            content=f"Database error: {e}"
        )
    
    finally:
        if engine:
            engine.dispose()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)