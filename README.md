# Wingz Ride Management API

A Django REST Framework-based API for managing ride information, including users, rides, and ride events. The API supports comprehensive ride management with features like filtering, sorting, and pagination.

## Features

* 🔐 Role-based authentication (Admin access)
* 📝 Complete CRUD operations for rides
* 🔍 Advanced filtering and sorting capabilities
* 📊 Efficient pagination
* 📅 Recent events tracking (24-hour window)
* 📍 Distance-based sorting
* 📖 API documentation 

## Technical Stack

* Python 3.8+
* Django 4.2+
* Django REST Framework
* PostMan collections (API documentation)
* SQLite/PostgreSQL

## Setup Instructions

### 1. Clone the Repository


# Git Clone Repository

```bash
git clone git@github.com:RichardKaranuMbuti/wingz.git
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

Generate or paste your environment variables
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

- Ridelist endpoint require authentication by JWT tokens so first generate them by logging in first
- Only users with 'admin' role can access the API(Ride List).
- Use Token Authentication: Include `Authorization: Token <your-token>` in headers.
- The provided postman collection has this provided and saved. 
- See the tutorial below, 


## Signup endpoint
You need to signup first before getting authenticated for the protected endpoints

## Signup Endpoint (`/api/register/`)

Request body 
```json
{
 "email": "notadmin@gmail.com",
 "role": "user",
 "password": "admin123!",
 "username": "notadmin1",
 "first_name": "Paul",
 "last_name": "Jeff",
 "phone_number": "0785634567"
 }

 ```


## Login endpoint
Upon successful authetication it provides you with both access and refesh tokens


## login  (`/api/token/`)

Request body 
```json
{
 "email": "notadmin@gmail.com",
 "password": "admin123!",
 }
 
 ```


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

Access the comprehensive API documentation:

- Postman Collections : https://documenter.getpostman.com/view/28229446/2sAYBXCX4t

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




# SQL query 

## Trip Duration Analysis
The following SQL query analyzes rides that took more than 1 hour to complete, aggregated by month and driver. This query specifically tracks the duration between pickup and dropoff states.

Create the index

```sql
CREATE INDEX IF NOT EXISTS idx_ride_event_desc_created ON ride_event(description, created_at);
```

Then;

```sql
WITH trip_durations AS (
    SELECT 
        r.id_ride,
        r.id_driver_id,
        u.first_name || ' ' || SUBSTR(u.last_name, 1, 1) as driver_name,
        MIN(CASE WHEN re.description = 'Status changed to pickup' THEN re.created_at END) as pickup_time,
        MIN(CASE WHEN re.description = 'Status changed to dropoff' THEN re.created_at END) as dropoff_time,
        DATE_TRUNC('month', re.created_at) as month
    FROM ride r
    JOIN user u ON r.id_driver_id = u.id
    JOIN ride_event re ON r.id_ride = re.id_ride_id
    WHERE r.status = 'dropoff'  -- Only completed rides
    GROUP BY 
        r.id_ride,
        r.id_driver_id,
        u.first_name,
        u.last_name,
        DATE_TRUNC('month', re.created_at)
    HAVING 
        MIN(CASE WHEN re.description = 'Status changed to pickup' THEN re.created_at END) IS NOT NULL
        AND MIN(CASE WHEN re.description = 'Status changed to dropoff' THEN re.created_at END) IS NOT NULL
)
SELECT 
    TO_CHAR(month, 'YYYY-MM') as month,
    driver_name as "Driver",
    COUNT(*) as "Count of Trips > 1 hr"
FROM trip_durations
WHERE 
    EXTRACT(EPOCH FROM (dropoff_time - pickup_time)) > 3600  -- More than 1 hour in seconds
GROUP BY 
    month,
    driver_name
ORDER BY 
    month,
    driver_name;

```

### Justification

- Efficient Data Processing

  - Uses CTE to compute trip durations once
  - Filters completed rides early with status = 'dropoff'
  - Handles driver name formatting (first_name + last initial) in the CTE


- Data Integrity:

  - HAVING clause ensures we only include rides with both pickup and dropoff events
  - Matches the exact sample output format


- Performance Considerations

  - Uses existing indexes on foreign keys
  - Performs date truncation and formatting efficiently
  - Groups data at appropriate stages to minimize processing

# Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

# License

This project is licensed under the MIT License - see the `LICENSE` file for details.