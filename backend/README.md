# Blog API

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available under `/api`:

- `GET /api/posts?offset=0&limit=20&is_published=true`
- `GET /api/posts/{id-or-slug}`
- `GET /api/posts/id/{id}`
- `GET /api/posts/slug/{slug}`
- `POST /api/posts`
- `PUT /api/posts/{id}`
- `DELETE /api/posts/{id}`

## Database and migrations

The default database is SQLite at `./blog.db`. Set `DATABASE_URL` to use another
SQLAlchemy asynchronous URL, such as `postgresql+psycopg://user:password@host/db`.

Run migrations with:

```bash
alembic upgrade head
```

`CORS_ORIGINS` accepts a comma-separated list of allowed origins. The default is
`http://localhost:3000`.
