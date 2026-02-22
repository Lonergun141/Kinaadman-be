import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant, TenantBranding, TenantPolicy, TenantEmailDomain
from apps.users.models import TenantMembership
from apps.repository.models import (
    Department, Program, Thesis, ThesisStatusHistory, ThesisReview,
    ThesisAuthor, ThesisAdviser, Keyword, ThesisKeyword, FileObject, ThesisFile
)
import uuid

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = 'Populate the database with mock data for Kinaadman'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting mock data population...')

        # 1. Tenants
        tenant1 = Tenant.objects.create(name='University of Kinaadman', slug='uok')
        tenant2 = Tenant.objects.create(name='Global Tech Institute', slug='gti')
        
        TenantBranding.objects.create(tenant=tenant1, display_name='UoK', primary_color='#0055A4')
        TenantBranding.objects.create(tenant=tenant2, display_name='GTI', primary_color='#D9381E')
        
        TenantPolicy.objects.create(tenant=tenant1, campus_only=True)
        TenantPolicy.objects.create(tenant=tenant2, campus_only=False)

        TenantEmailDomain.objects.create(tenant=tenant1, domain='uok.edu.ph')
        TenantEmailDomain.objects.create(tenant=tenant2, domain='gti.edu')

        # 2. Users & Memberships
        for email, role in [
            ('admin@uok.edu.ph', 'TENANT_ADMIN'),
            ('librarian@uok.edu.ph', 'LIBRARIAN'),
            ('adviser1@uok.edu.ph', 'ADVISER'),
            ('adviser2@uok.edu.ph', 'ADVISER'),
            ('student1@uok.edu.ph', 'STUDENT'),
            ('student2@uok.edu.ph', 'STUDENT'),
            ('student3@uok.edu.ph', 'STUDENT')
        ]:
            user, created = User.objects.get_or_create(email=email)
            if created:
                user.set_password('password123')
                user.is_active = True
                user.email_verification_status = 'VERIFIED'
                user.save()
            TenantMembership.objects.get_or_create(tenant=tenant1, user=user, role=role)

        # 3. Departments & Programs
        dept_cs = Department.objects.create(tenant=tenant1, name='College of Computer Studies')
        dept_eng = Department.objects.create(tenant=tenant1, name='College of Engineering')

        prog_bsit = Program.objects.create(tenant=tenant1, department=dept_cs, name='BS Information Technology')
        prog_bscs = Program.objects.create(tenant=tenant1, department=dept_cs, name='BS Computer Science')
        prog_bsce = Program.objects.create(tenant=tenant1, department=dept_eng, name='BS Civil Engineering')

        # 4. Keywords
        k_ml = Keyword.objects.create(tenant=tenant1, value='Machine Learning')
        k_ai = Keyword.objects.create(tenant=tenant1, value='Artificial Intelligence')
        k_web = Keyword.objects.create(tenant=tenant1, value='Web Development')
        k_data = Keyword.objects.create(tenant=tenant1, value='Data Science')

        # 5. Theses
        student1_member = TenantMembership.objects.get(user__email='student1@uok.edu.ph', tenant=tenant1)
        student2_member = TenantMembership.objects.get(user__email='student2@uok.edu.ph', tenant=tenant1)
        adviser1_member = TenantMembership.objects.get(user__email='adviser1@uok.edu.ph', tenant=tenant1)
        adviser2_member = TenantMembership.objects.get(user__email='adviser2@uok.edu.ph', tenant=tenant1)
        librarian_member = TenantMembership.objects.get(user__email='librarian@uok.edu.ph', tenant=tenant1)

        for i in range(5):
            status = random.choice(['DRAFT', 'SUBMITTED', 'IN_REVIEW', 'APPROVED', 'PUBLISHED'])
            is_published = status == 'PUBLISHED'
            
            thesis = Thesis.objects.create(
                tenant=tenant1,
                title=fake.catch_phrase(),
                abstract=fake.paragraph(nb_sentences=5),
                year=2025 if random.choice([True, False]) else 2026,
                status=status,
                department=dept_cs,
                program=random.choice([prog_bscs, prog_bsit]),
                created_by_membership=student1_member if i % 2 == 0 else student2_member,
                published_at=timezone.now() if is_published else None
            )

            # Authors
            ThesisAuthor.objects.create(
                tenant=tenant1,
                thesis=thesis,
                user=student1_member.user if i % 2 == 0 else student2_member.user,
                display_name=fake.name(),
                sort_order=1
            )
            
            # Adviser
            ThesisAdviser.objects.create(
                tenant=tenant1,
                thesis=thesis,
                adviser_membership=adviser1_member if i % 2 == 0 else adviser2_member
            )

            # Keywords
            ThesisKeyword.objects.create(tenant=tenant1, thesis=thesis, keyword=random.choice([k_ml, k_ai]))
            ThesisKeyword.objects.create(tenant=tenant1, thesis=thesis, keyword=random.choice([k_web, k_data]))

            # Reviews
            if status in ['IN_REVIEW', 'APPROVED', 'PUBLISHED']:
                ThesisReview.objects.create(
                    tenant=tenant1,
                    thesis=thesis,
                    reviewer_membership=adviser1_member,
                    decision='APPROVED' if status in ['APPROVED', 'PUBLISHED'] else 'PENDING',
                    comment=fake.sentence()
                )

            # Files
            file_obj = FileObject.objects.create(
                tenant=tenant1,
                provider='S3',
                bucket='kinaadman-bucket',
                object_key=f'theses/{thesis.id}/main.pdf',
                filename='main_thesis.pdf',
                content_type='application/pdf',
                size_bytes=random.randint(1000000, 5000000)
            )

            ThesisFile.objects.create(
                tenant=tenant1,
                thesis=thesis,
                file_object=file_obj,
                kind='MAIN_PDF',
                uploaded_by_membership=thesis.created_by_membership
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated the database with mock data'))
