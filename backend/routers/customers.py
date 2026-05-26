from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..models import CustomerListData, CustomerRecord, SaveCustomerRequest
from ..responses import success
from ..services.customers import create_customer_record, read_customers, write_customers


router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
def list_customers(
    customer_name: str | None = Query(None, alias="customerName"),
    level: str | None = Query(None),
    status: str | None = Query(None),
):
    customers = read_customers(get_settings().customers_file)

    def matches(record: CustomerRecord) -> bool:
        return (
            (not customer_name or customer_name.lower() in record.customerName.lower())
            and (not level or record.level == level)
            and (not status or record.status == status)
        )

    filtered = [record for record in customers if matches(record)]
    return success(CustomerListData(list=filtered, total=len(filtered)))


@router.post("")
def create_customer(payload: SaveCustomerRequest):
    settings = get_settings()
    customers = read_customers(settings.customers_file)
    customer = create_customer_record(payload)
    customers.insert(0, customer)
    write_customers(settings.customers_file, customers)
    return success(customer, message="客户创建成功")


@router.put("/{customer_id}")
def update_customer(customer_id: str, payload: SaveCustomerRequest):
    settings = get_settings()
    customers = read_customers(settings.customers_file)
    for index, customer in enumerate(customers):
        if customer.id != customer_id:
            continue
        updated = CustomerRecord(
            id=customer.id,
            customerName=payload.customerName,
            level=payload.level,
            contactName=payload.contactName,
            phone=payload.phone,
            region=payload.region,
            status=payload.status,
            createdAt=payload.createdAt or customer.createdAt,
        )
        customers[index] = updated
        write_customers(settings.customers_file, customers)
        return success(updated, message="客户更新成功")

    raise HTTPException(status_code=404, detail="Customer not found")


@router.delete("/{customer_id}")
def delete_customer(customer_id: str):
    settings = get_settings()
    customers = read_customers(settings.customers_file)
    filtered = [customer for customer in customers if customer.id != customer_id]
    if len(filtered) == len(customers):
        raise HTTPException(status_code=404, detail="Customer not found")
    write_customers(settings.customers_file, filtered)
    return success({"id": customer_id}, message="客户删除成功")
