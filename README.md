# Billing Count using Map/Reduce

I am using Google's Map/Reduce and Apache Beam, a practical tool, to streamline my billing data processing. This includes calculating the total amount each customer has spent on Google Cloud Platform (GCP) services. Additionally, I am utilizing Apache Beam to continuously receive streaming data published by the Pub/Sub service. I employ windowing techniques to segment the unbounded data into smaller windows.

## Map Reduce Implement

- Input reader 
    - Read streaming data from Pub/Sub service publications in GCP and partition it into windows:
    ```
        beam.WindowInto(
            FixedWindows(1*5) , 
            trigger=AfterAny(AfterWatermark( 
                early=AfterProcessingTime(10),
                late=AfterProcessingTime(30)
            )),
            accumulation_mode=AccumulationMode.DISCARDING
        )
    ```
- Map Phase
    - `Map(k1,v1) → list(k2,v2)`
    ```
      beam.Map(lambda billing: (billing.company, billing.cost))  
    ```
- Reduce Phase
    - `Reduce(k2, list (v2)) → list((k3, v3))`
    ```
        beam.CombinePerKey(sum)
    ```

## Running Platform 
- DataFlow

## Tools Used
- Apache beam
- GCP Pub/Sub 
- Cloud SQL (MySQL)

## Impact
By applying Map/Reduce to our billing counting system, we have significantly reduced the processing time for handling large volumes of data. The parallel processing capabilities of Map/Reduce allow for concurrent processing of billing data from different companies, resulting in faster and more efficient calculations.

--- 
## Start Service
1. Create and Activate virtual environment
```
python3 -m venv ma_venv
source ma_venv
```
2. Install required packages
```
pip install requirements.txt
```
3. Set google environment variable
```
export GOOGLE_APPLICATION_CREDENTIALS=/Users/apple/Code/Ann/master/service-account-key.json
```
4. Run the app
```
flask --app ann_app run --debug
```