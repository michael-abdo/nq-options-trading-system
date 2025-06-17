#!/usr/bin/env python3
import databento as db
import os

# Simplest possible test
client = db.Live(key=os.getenv('DATABENTO_API_KEY'))

# Print one record
def print_record(record):
    print(f"GOT DATA: {record}")
    client.stop()

client.add_callback(print_record)

client.subscribe(
    dataset='GLBX.MDP3',
    symbols=['NQ.c.0'],
    schema='mbp-1'
)

print("Starting...")
client.start()

# Block until stopped
client.block_for_close()
print("Done")
