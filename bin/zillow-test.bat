REM v20260309-1
REM set RAPIDAPI_KEY=b7da9a81eamshae67de73bb4cb7ep180846jsn27eed1c3565f
set RAPIDAPI_KEY=b7da9a81eamshae67de73bb4cb7ep180846jsn27eed1c3565f
curl --request GET --url "https://us-property-data.p.rapidapi.com/api/v1/search/by-location?location=29401&page=1" --header "x-rapidapi-host: us-property-data.p.rapidapi.com" --header "x-rapidapi-key: %RAPIDAPI_KEY%"

pause 

curl --request GET --url "https://us-property-data.p.rapidapi.com/api/v1/search/by-location?location=29401&page=1&listing_status=for_sale&sort_by=globalrelevanceex" --header "x-rapidapi-host: us-property-data.p.rapidapi.com" --header "x-rapidapi-key: %RAPIDAPI_KEY%"


GET /api/v1/search/by-location?location=138-23%20Newyork%2C%20Rosedale%2C%20NY%2011422&page=1&listing_status=for_sale&sort_by=globalrelevanceex HTTP/1.1
X-Rapidapi-Key: *************
X-Rapidapi-Host: us-property-data.p.rapidapi.com
Host: us-property-data.p.rapidapi.com

set RAPIDAPI_KEY=b7da9a81eamshae67de73bb4cb7ep180846jsn27eed1c3565f
set "URL=https://us-property-data.p.rapidapi.com/api/v1/search/by-location?location=29401&listing_status=for_sale&sort_by=globalrelevanceex&page=1"
set "URL=https://us-property-data.p.rapidapi.com/api/v1/search/by-location?location=29414&listing_status=for_sale&sort_by=globalrelevanceex&page=1"
curl --request GET --url "%URL%" --header "x-rapidapi-host: us-property-data.p.rapidapi.com" --header "x-rapidapi-key: %RAPIDAPI_KEY%"

