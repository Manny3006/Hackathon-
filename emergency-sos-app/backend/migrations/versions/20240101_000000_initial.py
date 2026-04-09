"""Create initial tables for Emergency SOS system

Revision ID: initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    sa.Enum('cardiac', 'trauma', 'stroke', 'fire', 'accident', 'general', name='emergencytype').create(op.get_bind())
    sa.Enum('triggered', 'hospital_selected', 'ambulance_dispatched', 'en_route_to_patient', 
            'patient_picked', 'en_route_to_hospital', 'arrived_at_hospital', 'completed', 'cancelled', 
            name='emergencystatus').create(op.get_bind())
    sa.Enum('available', 'dispatched', 'en_route', 'occupied', 'maintenance', name='ambulancestatus').create(op.get_bind())
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('blood_type', sa.String(length=5), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('medical_conditions', sa.Text(), nullable=True),
        sa.Column('emergency_contacts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('home_address', sa.Text(), nullable=True),
        sa.Column('home_latitude', sa.Float(), nullable=True),
        sa.Column('home_longitude', sa.Float(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)
    
    # Create hospitals table
    op.create_table('hospitals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('location', postgresql.GEOMETRY(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('specialties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('total_beds', sa.Integer(), nullable=True),
        sa.Column('available_beds', sa.Integer(), nullable=True),
        sa.Column('has_emergency_ward', sa.Boolean(), nullable=True),
        sa.Column('has_trauma_center', sa.Boolean(), nullable=True),
        sa.Column('has_cardiology', sa.Boolean(), nullable=True),
        sa.Column('has_neurology', sa.Boolean(), nullable=True),
        sa.Column('has_pediatrics', sa.Boolean(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hospitals_id'), 'hospitals', ['id'], unique=False)
    op.create_index(op.f('ix_hospitals_name'), 'hospitals', ['name'], unique=False)
    
    # Create ambulances table
    op.create_table('ambulances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_number', sa.String(length=20), nullable=False),
        sa.Column('driver_name', sa.String(length=255), nullable=True),
        sa.Column('driver_phone', sa.String(length=20), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('location', postgresql.GEOMETRY(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('status', sa.Enum('available', 'dispatched', 'en_route', 'occupied', 'maintenance', name='ambulancestatus'), nullable=True),
        sa.Column('assigned_emergency_id', sa.Integer(), nullable=True),
        sa.Column('has_life_support', sa.Boolean(), nullable=True),
        sa.Column('has_defibrillator', sa.Boolean(), nullable=True),
        sa.Column('has_oxygen', sa.Boolean(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vehicle_number')
    )
    op.create_index(op.f('ix_ambulances_id'), 'ambulances', ['id'], unique=False)
    
    # Create emergencies table
    op.create_table('emergencies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('emergency_type', sa.Enum('cardiac', 'trauma', 'stroke', 'fire', 'accident', 'general', name='emergencytype'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('location', postgresql.GEOMETRY(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('assigned_hospital_id', sa.Integer(), nullable=True),
        sa.Column('assigned_ambulance_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('triggered', 'hospital_selected', 'ambulance_dispatched', 'en_route_to_patient', 
                                    'patient_picked', 'en_route_to_hospital', 'arrived_at_hospital', 'completed', 'cancelled', 
                                    name='emergencystatus'), nullable=True),
        sa.Column('tracking_token', sa.String(length=64), nullable=True),
        sa.Column('triggered_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('confirmed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('ambulance_dispatched_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('arrived_at_hospital_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['assigned_ambulance_id'], ['ambulances.id'], ),
        sa.ForeignKeyConstraint(['assigned_hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_index(op.f('ix_emergencies_id'), 'emergencies', ['id'], unique=False)
    op.create_index(op.f('ix_emergencies_tracking_token'), 'emergencies', ['tracking_token'], unique=True)
    
    # Create emergency_updates table
    op.create_table('emergency_updates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('emergency_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('triggered', 'hospital_selected', 'ambulance_dispatched', 'en_route_to_patient', 
                                   'patient_picked', 'en_route_to_hospital', 'arrived_at_hospital', 'completed', 'cancelled', 
                                   name='emergencystatus'), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['emergency_id'], ['emergencies.id'], )
    )
    op.create_index(op.f('ix_emergency_updates_id'), 'emergency_updates', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_emergency_updates_id'), table_name='emergency_updates')
    op.drop_table('emergency_updates')
    op.drop_index(op.f('ix_emergencies_tracking_token'), table_name='emergencies')
    op.drop_index(op.f('ix_emergencies_id'), table_name='emergencies')
    op.drop_table('emergencies')
    op.drop_index(op.f('ix_ambulances_id'), table_name='ambulances')
    op.drop_table('ambulances')
    op.drop_index(op.f('ix_hospitals_name'), table_name='hospitals')
    op.drop_index(op.f('ix_hospitals_id'), table_name='hospitals')
    op.drop_table('hospitals')
    op.drop_index(op.f('ix_users_phone'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Drop enum types
    sa.Enum(name='emergencystatus').drop(op.get_bind())
    sa.Enum(name='ambulancestatus').drop(op.get_bind())
    sa.Enum(name='emergencytype').drop(op.get_bind())
