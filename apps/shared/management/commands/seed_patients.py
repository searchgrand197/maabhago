"""
Management command to seed 500 realistic Indian patients.
Usage:  python manage.py seed_patients
        python manage.py seed_patients --count 200   (custom count)
        python manage.py seed_patients --clear        (delete existing patients first)
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.patients.models import Patient
from apps.patients.services.uhid_service import generate_uhid
from apps.shared.models import Hospital


FIRST_NAMES_MALE = [
    "Aarav", "Aditya", "Ajay", "Akash", "Amit", "Anand", "Arjun", "Ashok", "Deepak", "Dhruv",
    "Gaurav", "Harsh", "Hemant", "Karan", "Krishna", "Manoj", "Mohit", "Mukesh", "Nikhil", "Nilesh",
    "Pankaj", "Pranav", "Prateek", "Rahul", "Raj", "Rajesh", "Rakesh", "Ram", "Ravi", "Ritesh",
    "Rohit", "Sachin", "Sanjay", "Santosh", "Shubham", "Siddharth", "Sunil", "Suresh", "Tarun", "Vijay",
    "Vikram", "Vinay", "Vishal", "Vivek", "Yogesh", "Lokesh", "Manish", "Naveen", "Omkar", "Parth",
    "Abhishek", "Alok", "Anil", "Anirudh", "Ankit", "Bharat", "Chetan", "Dinesh", "Girish", "Hitesh",
    "Jitendra", "Kapil", "Kuldeep", "Lalit", "Mahesh", "Mayur", "Neeraj", "Nitin", "Piyush", "Pramod",
    "Prashant", "Ravindra", "Sagar", "Shailesh", "Shyam", "Soham", "Sumit", "Swapnil", "Uday", "Umesh",
]

FIRST_NAMES_FEMALE = [
    "Aarti", "Ananya", "Ankita", "Anushka", "Archana", "Deepika", "Divya", "Geeta", "Ishita", "Jyoti",
    "Kajal", "Kavita", "Komal", "Lakshmi", "Lata", "Manisha", "Meena", "Meera", "Nandini", "Neha",
    "Pallavi", "Poonam", "Pooja", "Prachi", "Pragya", "Priya", "Radha", "Rashmi", "Rekha", "Ritu",
    "Sakshi", "Sangeeta", "Seema", "Shikha", "Shreya", "Sneha", "Sonali", "Sunita", "Swati", "Usha",
    "Vandana", "Varsha", "Vidya", "Yamini", "Yashoda", "Zoya", "Nisha", "Roshni", "Tanvi", "Shruti",
    "Aisha", "Amita", "Bindiya", "Chhaya", "Durga", "Farida", "Gita", "Heena", "Indira", "Kiran",
    "Lalita", "Madhuri", "Mamta", "Namrata", "Nutan", "Payal", "Pushpa", "Reena", "Rupali", "Savita",
    "Shobha", "Sudha", "Sushma", "Tara", "Uma", "Veena", "Vineeta", "Yogita", "Zainab", "Sonal",
]

LAST_NAMES = [
    "Agarwal", "Bhat", "Bose", "Chaturvedi", "Chaudhary", "Chauhan", "Chopra", "Das", "Dave", "Desai",
    "Dixit", "Dubey", "Dutta", "Gandhi", "Ghosh", "Goswami", "Gupta", "Iyer", "Jain", "Jha",
    "Joshi", "Kapoor", "Kaur", "Khan", "Khanna", "Kumar", "Lal", "Malhotra", "Mehta", "Mishra",
    "Mukherjee", "Nair", "Nanda", "Pandey", "Patel", "Pathak", "Pillai", "Rao", "Reddy", "Roy",
    "Saxena", "Shah", "Sharma", "Shukla", "Singh", "Sinha", "Srivastava", "Tiwari", "Varma", "Yadav",
    "Ahuja", "Anand", "Arora", "Bajaj", "Bansal", "Batra", "Bhatt", "Chhabra", "Dewan", "Dhawan",
    "Garg", "Goel", "Goyal", "Gulati", "Hora", "Khurana", "Kohli", "Lamba", "Luthra", "Madan",
    "Mahajan", "Narang", "Oberoi", "Pasricha", "Punjabi", "Sachdeva", "Sahni", "Sethi", "Sodhi", "Walia",
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", ""]

PATIENT_TYPES = ["general", "vip", "staff", ""]


def random_dob() -> date:
    start = date(1940, 1, 1)
    end = date(2015, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_phone(used_phones: set) -> str:
    for _ in range(10000):
        prefix = random.choice(["6", "7", "8", "9"])
        rest = "".join([str(random.randint(0, 9)) for _ in range(9)])
        num = prefix + rest
        if num not in used_phones:
            used_phones.add(num)
            return num
    raise RuntimeError("Cannot generate a unique phone number")


class Command(BaseCommand):
    help = "Seed 500 realistic Indian patients into the database"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=500, help="Number of patients to create (default: 500)")
        parser.add_argument("--clear", action="store_true", help="Delete existing patients before seeding")

    def handle(self, *args, **options):
        count = options["count"]
        clear = options["clear"]

        hospital = Hospital.objects.first()
        if not hospital:
            self.stderr.write(self.style.ERROR("No hospital found. Run seed_initial first."))
            return

        self.stdout.write(f"Hospital: {self.style.SUCCESS(hospital.name)}")

        if clear:
            deleted, _ = Patient.objects.filter(hospital=hospital).delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing patients.")
)

        used_phones: set = set(
            Patient.objects.filter(hospital=hospital).values_list("phone", flat=True)
        )

        created = 0
        batch: list[Patient] = []

        with transaction.atomic():
            for i in range(count):
                gender = random.choice(["male", "female"])
                first = random.choice(FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE)
                last = random.choice(LAST_NAMES)
                phone = random_phone(used_phones)
                dob = random_dob()
                blood = random.choice(BLOOD_GROUPS)
                ptype = random.choice(PATIENT_TYPES)
                uhid = generate_uhid(hospital)

                batch.append(Patient(
                    hospital=hospital,
                    uhid=uhid,
                    first_name=first,
                    last_name=last,
                    gender=gender,
                    dob=dob,
                    phone=phone,
                    blood_group=blood,
                    patient_type=ptype,
                    status="active",
                ))
                created += 1

                if len(batch) >= 50:
                    Patient.objects.bulk_create(batch)
                    self.stdout.write(f"  [{created}/{count}] patients created...")
                    batch = []

            if batch:
                Patient.objects.bulk_create(batch)

        total = Patient.objects.filter(hospital=hospital).count()
        self.stdout.write(self.style.SUCCESS(
            f"Done! {created} patients created. Total in DB: {total}"
        ))
