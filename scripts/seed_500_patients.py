"""
Seed 500 realistic Indian patients.
Run: python manage.py shell < scripts/seed_500_patients.py
"""
import random
from datetime import date

from apps.patients.models import Patient
from apps.patients.services.uhid_service import generate_uhid
from apps.shared.models import Hospital

hospital = Hospital.objects.first()
if not hospital:
    print("❌ No hospital found. Run seed_initial first.")
    raise SystemExit

print(f"✅ Using hospital: {hospital.name}")

FIRST_NAMES_MALE = [
    "Aarav","Aditya","Ajay","Akash","Amit","Anand","Arjun","Ashok","Deepak","Dhruv",
    "Gaurav","Harsh","Hemant","Karan","Krishna","Manoj","Mohit","Mukesh","Nikhil","Nilesh",
    "Pankaj","Pranav","Prateek","Rahul","Raj","Rajesh","Rakesh","Ram","Ravi","Ritesh",
    "Rohit","Sachin","Sanjay","Santosh","Shubham","Siddharth","Sunil","Suresh","Tarun","Vijay",
    "Vikram","Vinay","Vishal","Vivek","Yogesh","Lokesh","Manish","Naveen","Omkar","Parth",
]

FIRST_NAMES_FEMALE = [
    "Aarti","Ananya","Ankita","Anushka","Archana","Deepika","Divya","Geeta","Ishita","Jyoti",
    "Kajal","Kavita","Komal","Lakshmi","Lata","Manisha","Meena","Meera","Nandini","Neha",
    "Pallavi","Poonam","Pooja","Prachi","Pragya","Priya","Radha","Rashmi","Rekha","Ritu",
    "Sakshi","Sangeeta","Seema","Shikha","Shreya","Sneha","Sonali","Sunita","Swati","Usha",
    "Vandana","Varsha","Vidya","Yamini","Yashoda","Zoya","Nisha","Roshni","Tanvi","Shruti",
]

LAST_NAMES = [
    "Agarwal","Bhat","Bose","Chaturvedi","Chaudhary","Chauhan","Chopra","Das","Dave","Desai",
    "Dixit","Dubey","Dutta","Gandhi","Ghosh","Goswami","Gupta","Iyer","Jain","Jha",
    "Joshi","Kapoor","Kaur","Khan","Khanna","Kumar","Lal","Malhotra","Mehta","Mishra",
    "Mukherjee","Nair","Nanda","Pandey","Patel","Pathak","Pillai","Rao","Reddy","Roy",
    "Saxena","Shah","Sharma","Shukla","Singh","Sinha","Srivastava","Tiwari","Varma","Yadav",
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

CITIES = [
    "Mumbai","Delhi","Bengaluru","Hyderabad","Ahmedabad","Chennai","Kolkata","Pune",
    "Jaipur","Lucknow","Kanpur","Nagpur","Indore","Thane","Bhopal","Visakhapatnam",
    "Patna","Vadodara","Ghaziabad","Ludhiana","Agra","Nashik","Faridabad","Meerut","Surat",
]

def random_dob():
    start = date(1950, 1, 1)
    end   = date(2010, 12, 31)
    days  = (end - start).days
    return start.replace(year=0) if False else date.fromordinal(start.toordinal() + random.randint(0, days))

def random_phone(used):
    while True:
        # Indian mobile: starts with 6-9
        prefix = random.choice(["6","7","8","9"])
        rest   = "".join([str(random.randint(0,9)) for _ in range(9)])
        num    = prefix + rest
        if num not in used:
            used.add(num)
            return num

used_phones = set(Patient.objects.values_list("phone", flat=True))
created_count = 0
skipped_count = 0

for i in range(500):
    gender = random.choice(["male", "female"])
    first  = random.choice(FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE)
    last   = random.choice(LAST_NAMES)
    phone  = random_phone(used_phones)
    dob    = random_dob()
    city   = random.choice(CITIES)
    blood  = random.choice(BLOOD_GROUPS)

    uhid = generate_uhid(hospital)
    Patient.objects.create(
        hospital    = hospital,
        uhid        = uhid,
        first_name  = first,
        last_name   = last,
        gender      = gender,
        dob         = dob,
        phone       = phone,
        blood_group = blood,
        status      = "active",
    )
    created_count += 1
    if (i + 1) % 50 == 0:
        print(f"  → {i+1}/500 patients created…")

print(f"\n✅ Done! {created_count} patients created, {skipped_count} skipped.")
print(f"   Total patients in DB: {Patient.objects.filter(hospital=hospital).count()}")
