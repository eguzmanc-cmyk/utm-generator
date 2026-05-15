import unittest
from datetime import date

from core.utm_generator import (
    generate_master_utm_id,
    generate_utm_url,
    prepare_utm_record,
    validate_utm_data,
)


class UTMGeneratorTests(unittest.TestCase):
    def test_generate_master_utm_id_uses_month_prefix_and_increment(self):
        existing_ids = ["MAY26-00001", "MAY26-00004", "ABR26-00099"]
        next_id = generate_master_utm_id(existing_ids, date(2026, 5, 6))
        self.assertEqual(next_id, "MAY26-00005")

    def test_validate_utm_data_requires_zc_when_seasonal(self):
        errors = validate_utm_data(
            {
                "website_url": "https://www.gbm.com",
                "utm_source": "Meta",
                "utm_medium": "Paid Social",
                "utm_name": "Buen Fin",
                "utm_intent": "Leads",
                "utm_business": "Advisory",
                "owner": "Nico",
                "is_seasonal": True,
                "utm_zc": "",
            }
        )
        self.assertIn(
            "UTM SC es requerido cuando la campaña es de estacionalidad",
            errors,
        )

    def test_prepare_record_and_generate_url_include_master_fields(self):
        record = prepare_utm_record(
            {
                "website_url": "gbm.com/landing",
                "utm_source": "Meta",
                "utm_medium": "Paid Social",
                "utm_name": "Advisory Leads Q2",
                "utm_intent": "Leads",
                "utm_business": "Advisory",
                "utm_campaign_id": "111",
                "utm_asset_id": "55555",
                "utm_term": "credito",
                "utm_content": "video",
                "utm_zc": "Buen Fin",
                "owner": "Nico",
                "description": "Regla principal",
                "is_seasonal": True,
            },
            existing_ids=["MAY26-00001"],
            reference_date=date(2026, 5, 6),
        )

        generated_url = generate_utm_url(record["website_url"], record)

        self.assertEqual(record["utm_id"], "MAY26-00002")
        self.assertEqual(record["utm_created"], "2026-05-06")
        self.assertIn("utm_source=meta", generated_url)
        self.assertIn("utm_medium=paid_social", generated_url)
        self.assertIn("utm_campaign=advisory_leads_q2", generated_url)
        self.assertIn("utm_id=MAY26-00002", generated_url)
        self.assertIn("utm_zc=buen_fin", generated_url)
        self.assertIn("utm_campaign_id=111", generated_url)
        self.assertTrue(generated_url.startswith("https://gbm.com/landing?"))


if __name__ == "__main__":
    unittest.main()
