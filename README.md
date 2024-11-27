# Wingz Ride Management API

A Django REST Framework-based API for managing ride information, including users, rides, and ride events. The API supports comprehensive ride management with features like filtering, sorting, and pagination.

## Features

* 🔐 Role-based authentication (Admin access)
* 📝 Complete CRUD operations for rides
* 🔍 Advanced filtering and sorting capabilities
* 📊 Efficient pagination
* 📅 Recent events tracking (24-hour window)
* 📍 Distance-based sorting
* 📖 Interactive API documentation (Swagger/ReDoc)

## Technical Stack

* Python 3.8+
* Django 4.2+
* Django REST Framework
* drf-spectacular (API documentation)
* SQLite/PostgreSQL

## Setup Instructions

### 1. Clone the Repository


# Git Clone Repository

```bash
git clone <repository-url>
cd wingz
```

## 2. Create and Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Environment Setup

Create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
```

## 5. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

## 6. Create Admin User

```bash
python manage.py createsuperuser
```

## 7. Run Development Server

```bash
python manage.py runserver
```

# API Endpoints

## Authentication

- All endpoints require authentication.
- Only users with 'admin' role can access the API.
- Use Token Authentication: Include `Authorization: Token <your-token>` in headers.

## Rides Endpoint (`/api/rides/`)

### List Rides (`GET /api/rides/`)

- Supports pagination
- Query Parameters:
  - `page`: Page number (default: 1)
  - `page_size`: Items per page (default: 10, max: 100)
  - `status`: Filter by ride status (`'en-route'`, `'pickup'`, `'dropoff'`)
  - `rider_email`: Filter by rider's email
  - `sort_by`: Sort by `'pickup_time'` or `'distance'`
  - `latitude`: Required for distance sorting
  - `longitude`: Required for distance sorting

#### Example Request:

```bash
curl -X GET "http://localhost:8000/api/rides/?status=en-route&sort_by=distance&latitude=37.7749&longitude=-122.4194" \
     -H "Authorization: Token YOUR_TOKEN"
```

### Create Ride (`POST /api/rides/`)

#### Request Body:

```json
{
    "status": "en-route",
    "id_rider": 1,
    "id_driver": 2,
    "pickup_latitude": 37.7749,
    "pickup_longitude": -122.4194,
    "dropoff_latitude": 37.7750,
    "dropoff_longitude": -122.4195,
    "pickup_time": "2024-11-27T10:00:00Z"
}
```

### Get Single Ride (`GET /api/rides/{id}/`)

Returns detailed ride information including:

- Ride details
- Rider information
- Driver information
- Recent ride events (last 24 hours)

### Update Ride (`PUT/PATCH /api/rides/{id}/`)

- Supports both full updates (PUT) and partial updates (PATCH).

### Delete Ride (`DELETE /api/rides/{id}/`)

- Deletes the specified ride and its associated events.

## Response Formats

### Success Response

```json
{
    "count": 100,
    "next": "http://api/rides/?page=2",
    "previous": null,
    "results": [
        {
            "id_ride": 1,
            "status": "en-route",
            "rider": {
                "id_user": 1,
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone_number": "1234567890"
            },
            "driver": {
                "id_user": 2,
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "phone_number": "0987654321"
            },
            "pickup_latitude": 37.7749,
            "pickup_longitude": -122.4194,
            "dropoff_latitude": 37.7750,
            "dropoff_longitude": -122.4195,
            "pickup_time": "2024-11-27T10:00:00Z",
            "todays_ride_events": [
                {
                    "id_ride_event": 1,
                    "description": "Driver arrived",
                    "created_at": "2024-11-27T09:55:00Z"
                }
            ]
        }
    ]
}
```

### Error Response

```json
{
    "error": "Detailed error message",
    "status": 400
}
```

# Testing

## Run the test suite:

```bash
python manage.py test rides
```

## For verbose output:

```bash
python manage.py test rides -v 2
```

# API Documentation

Access the interactive API documentation:

- Swagger UI: [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)
- ReDoc: [http://localhost:8000/api/schema/redoc/](http://localhost:8000/api/schema/redoc/)

# Implementation Notes

## Design Decisions

### Performance Optimizations

- Used `select_related` for rider/driver information.
- Implemented `prefetch_related` for ride events.
- Limited ride events to last 24 hours.
- Added database indexes for frequently queried fields.

### Security

- Role-based access control.
- Input validation at serializer level.
- Proper error handling and logging.

### Scalability Considerations

- Efficient pagination implementation.
- Optimized database queries.
- Proper indexing for sorting and filtering.

## Challenges and Solutions

### Distance-Based Sorting

**Challenge**: Implementing efficient distance-based sorting for large datasets.  
**Solution**: Used database-level calculations instead of Python-level computation.

### Recent Events Filtering

**Challenge**: Efficiently retrieving only recent events without loading all events.  
**Solution**: Implemented custom prefetch queryset with time-based filtering.

### Query Optimization

**Challenge**: Keeping database queries minimal (requirement: 2-3 queries).  
**Solution**: Utilized proper prefetching and `select_related`.

# Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

# License

This project is licensed under the MIT License - see the `LICENSE` file for details.