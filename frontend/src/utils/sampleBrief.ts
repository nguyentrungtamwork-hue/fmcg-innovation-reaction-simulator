import type { BriefIn } from "../types/api";

// FreshPlus sample brief · mirrors samples/sample_innovation_brief.md so the
// dashboard demo flow exercises the real backend pipeline (not fake results).
export const SAMPLE_BRIEF_TEXT = `Brand: FreshPlus
Product: FreshPlus Herbal Cool · a ready-to-drink herbal tea with 50% less sugar.
Benefit: Refreshes naturally with less sugar; a calm reset in the afternoon.
Claims: 50% less sugar than leading RTD teas; contains chrysanthemum.
Packaging: 450ml frosted PET bottle. Price: slightly premium.
Target: urban office workers aged 22-35.
Occasions: mid-afternoon at work, after lunch, commute.
Channels: convenience stores, supermarkets, TikTok Shop.
Market: Vietnam. Competitors: mainstream bottled teas, zero-sugar teas.
Media: TikTok creators + 2 KOLs. Sampling: 4-week sampling at office CVS.
Promotion: BOGO at convenience chains.
Known risks: consumers may not believe the natural cooling claim; premium price may suppress trial; herbal taste may feel medicinal.`;

export const SAMPLE_BRIEF: BriefIn = {
  raw_text: SAMPLE_BRIEF_TEXT,
  brand: "FreshPlus",
  product_name: "FreshPlus Herbal Cool",
  category: "Ready-to-drink tea",
  benefit: "Refreshes naturally with less sugar",
  functional_claims: ["50% less sugar than leading RTD teas", "Contains chrysanthemum"],
  emotional_claims: ["A calm reset"],
  packaging: "450ml PET, frosted look",
  price: "Slightly premium",
  pack_size: "450ml",
  target_consumers: "Urban office workers 22-35",
  usage_occasions: ["mid-afternoon at work", "after lunch", "commute"],
  channels: ["Convenience stores", "Supermarkets", "TikTok Shop"],
  launch_market: "Vietnam",
  competitors: ["Mainstream bottled teas", "Zero-sugar teas"],
  media_plan: "TikTok creators, 2 KOLs",
  sampling_plan: "4-week sampling at office CVS",
  promotion_plan: "BOGO at convenience chains",
  known_risks: [
    "Consumers may not believe the natural cooling claim",
    "Premium price may suppress trial",
    "Herbal taste may feel medicinal",
  ],
};
