# Copyright 2019 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, fields, models, modules


class Users(models.Model):
    _inherit = "res.users"

    review_ids = fields.Many2many(string="Reviews", comodel_name="tier.review")

    @api.model
    def review_user_count(self):
        user_reviews = self.env["tier.review"].search(
            [
                ("id", "in", self.env.user.review_ids.ids),
                ("status", "=", "pending"),
                ("can_review", "=", True),
            ],
            order="id desc",
            limit=1000,
        )
        user_reviews_by_record_by_model_name = defaultdict(
            lambda: defaultdict(lambda: self.env["tier.review"])
        )
        for review in user_reviews:
            record = self.env[review.model].browse(review.res_id)
            user_reviews_by_record_by_model_name[review.model][record] += review
        model_ids = list(
            {
                self.env["ir.model"]._get(name).id
                for name in user_reviews_by_record_by_model_name.keys()
            }
        )
        user_reviews = {}
        for (
            model_name,
            user_reviews_by_record,
        ) in user_reviews_by_record_by_model_name.items():
            domain = [("id", "in", list({r.id for r in user_reviews_by_record.keys()}))]
            Model = self.env[model_name]
            allowed_records = Model.search(domain)
            if not allowed_records:
                continue
            module = Model._original_module
            icon = module and modules.module.get_module_icon(module)
            model = self.env["ir.model"]._get(model_name).with_prefetch(model_ids)
            user_reviews[model_name] = {
                "id": model.id,
                "name": model.name,
                "model": model_name,
                "active_field": "active" in model._fields,
                "icon": icon,
                "type": "tier_review",
                "pending_count": 0,
            }
            for record, review in user_reviews_by_record.items():
                if record not in allowed_records:
                    continue
                for user_review in review:
                    user_reviews[model_name]["pending_count"] += 1
        return list(user_reviews.values())
        # todo add test https://github.com/odoo/odoo/commit/a3260cfcd75f2804cf6aec916fdb159cddcca74f

    @api.model
    def get_reviews(self, data):
        review_obj = self.env["tier.review"].with_context(lang=self.env.user.lang)
        res = review_obj.search_read([("id", "in", data.get("res_ids"))])
        for r in res:
            # Get the translated status value.
            r["display_status"] = dict(
                review_obj.fields_get("status")["status"]["selection"]
            ).get(r.get("status"))
            # Convert to datetime timezone
            if r["reviewed_date"]:
                r["reviewed_date"] = fields.Datetime.context_timestamp(
                    self, r["reviewed_date"]
                )
        return res
