> ## Documentation Index
> Fetch the complete documentation index at: https://docs.polymarket.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Polymarket Changelog

> Welcome to the Polymarket Changelog. Here you will find any important changes to Polymarket, including but not limited to CLOB, API, UI and Mobile Applications.

<Update label="Mar 17, 2026" description="March Madness: $2M+ in Liquidity Rewards">
  * **March Madness Liquidity Rewards**: Adding \$2M+ in liquidity rewards to both live and pregame markets.
  * **How it works**: Liquidity rewards are payments for placing competitive bids. Rewards are paid out based on the size of your orders, how close they are to the midpoint, and how consistently they are quoted relative to other liquidity providers. Orders must be active on the book for a minimum of **3.5 seconds** to be eligible.

  **Daily reward rates for markets (subject to change):**

  **48 hours before GameStartTime:**

  * \$7.5k for full game ML market
  * \$500 for 5 other markets (most recently created full game spread, most recently created full game total, 1st half ML, most recently created 1st half spread, most recently created 1st half total)

  **From game live to game completion (note: rewards are expressed in daily rates):**

  * \$60k for full game ML
  * \$4k for most recently created full game spread and most recently created full game total

  **From game live to halftime (note: rewards are expressed in daily rates):**

  * \$8k for 1st half ML, most recently created 1st half spread, most recently created 1st half total

  * **Markets**: [Browse March Madness markets](https://polymarket.com/sports/cbb/games)

  * **More details**: [Liquidity Rewards documentation](/market-makers/liquidity-rewards#liquidity-rewards)
</Update>

<Update label="Mar 1, 2026" description="Taker Fees & Maker Rebates: All Crypto Markets">
  * **Crypto market fees expansion**: Starting March 6, 2026, taker fees and maker rebates extend to all crypto markets including 1H, 4H, daily, and weekly. The same fee structure as existing crypto markets applies. Only new markets created after March 6 are affected.
  * **Updated documentation**: [Fees](/trading/fees) and [Maker Rebates Program](/market-makers/maker-rebates) updated to reflect all crypto market coverage.
</Update>

<Update label="Feb 12, 2026" description="5-Minute Crypto Markets">
  * **5-minute crypto markets**: Launched with taker fees enabled. Fees follow the same curve as 15-minute crypto markets, peaking at 1.56% at 50% probability.
  * **Maker Rebates**: Liquidity providers earn daily USDC rebates funded by taker fees, same as 15-minute crypto markets.
</Update>

<Update label="Feb 11, 2026" description="Taker Fees & Maker Rebates: NCAAB and Serie A">
  * **Sports market fees**: Taker fees to be enabled on NCAAB (college basketball) and Serie A markets on February 18, 2026.
  * **Per-market rebate calculation**: Rebates are now calculated per market, makers only compete with other makers in the same market.
  * **Updated documentation**: [Maker Rebates Program](/market-makers/maker-rebates) updated with sports fee tables and parameters.
</Update>

<Update label="Jan 28, 2026" description="Bridge API: Withdrawal Endpoint">
  * **Withdrawal Endpoint**: New `/withdraw` endpoint to bridge USDC.e from Polymarket to any supported chain and token.
  * **Multi-chain withdrawals**: Withdraw to EVM chains (Ethereum, Arbitrum, Base, etc.), Solana, and Bitcoin.
  * **Updated documentation**: Bridge API docs updated to reflect deposit and withdrawal functionality.
</Update>

<Update label="Jan 16, 2026" description="Docs Update: RTDS documentation">
  * RTDS docs updated to reflect RTDS supports **comments** and **crypto prices** only.
  * Removed legacy CLOB references and `clob_auth` from RTDS docs.
</Update>

<Update label="Jan 16, 2026" description="Docs Update: Maker Rebates Program">
  * **Maker Rebates Program**: Updated funding schedule with distribution method (volume-weighted vs fee-curve weighted).
  * **Fee-curve weighted rebates**: Documented fee-equivalent formula and rebate calculation.
  * **FAQ**: Clarified how rebates are calculated during fee-curve weighted periods.
</Update>

<Update label="Jan 6, 2026" description="New API Features">
  * **Releases**: Daily Releases timing
  * **HeartBeats API**: HeartBeats endpoint for monitoring connection status and canceling orders
  * **Post Only Orders**: Orders that are rejected if they would immediately match against an existing order
</Update>

<Update label="Jan 5, 2026" description="Taker Fees & Maker Rebates">
  * **Taker Fees**: Enabled on 15-minute crypto markets. Fees vary by price and peak at 1.56% at 50% probability.
  * **Maker Rebates**: Daily USDC rebates paid to liquidity providers, funded by taker fees.
</Update>

<Update label="Sept 24, 2025" description="Polymarket Real-Time Data Socket (RTDS) official release">
  * **Crypto Price Feeds**: Access real-time cryptocurrency prices from two sources (Binance & Chainlink)
  * **Comment Streaming**: Real-time updates for comment events including new comments, replies, and reactions
  * **Dynamic Subscriptions**: Add, remove, and modify subscriptions without reconnecting
  * **TypeScript Client**: Official TypeScript client available at [real-time-data-client](https://github.com/Polymarket/real-time-data-client)
    For complete documentation, see [Market Data](/market-data/overview).
</Update>

<Update label="September 15, 2025" description="WSS price_change event update">
  * There has been a significant change to the structure of the price change message. This update will be applied at 11PM UTC September 15, 2025. We apologize for the short notice
    * Please see the [Market Channel](/market-data/websocket/market-channel) for details.
</Update>

<Update label="August 26, 2025" description="Updated /trades and /activity endpoints">
  * Reduced maximum values for query parameters on Data-API /trades and /activity:
    * `limit`: 500
    * `offset`: 1,000
</Update>

<Update label="August 21, 2025" description="Batch Orders Increase">
  * The batch orders limit has been increased from 5 -> 15. Read more about the batch orders functionality [here](/trading/orders/create).
</Update>

<Update label="July 23, 2025" description="Get Book(s) update">
  * We’re adding new fields to the `get-book` and `get-books` CLOB endpoints to include key market metadata that previously required separate queries.
    * `min_order_size`
      * type: string
      * description: Minimum price increment.
    * `neg_risk`
      * type: boolean
      * description: Boolean indicating whether the market is neg\_risk.
    * `tick_size`
      * type: string
      * description: Minimum price increment.
</Update>

<Update label="June 3, 2025" description="New Batch Orders Endpoint">
  * We’re excited to roll out a highly requested feature: **order batching**. With this new endpoint, users can now submit up to five trades in a single request. To help you get started, we’ve included sample code demonstrating how to use it. Please see [Create Orders](/trading/orders/create) for more details.
</Update>

<Update label="June 3, 2025" description="Change to /data/trades">
  * We're adding a new `side` field to the `MakerOrder` portion of the trade object. This field will indicate whether the maker order is a `buy` or `sell`, helping to clarify trade events where the maker side was previously ambiguous. For more details, refer to the MakerOrder object on the [Orders](/trading/orders/cancel) page.
</Update>

<Update label="May 28, 2025" description="Websocket Changes">
  * The 100 token subscription limit has been removed for the Markets channel. You can now subscribe to as many token IDs as needed for your use case.
  * New Subscribe Field `initial_dump`
    * Optional field to indicate whether you want to receive the initial order book state when subscribing to a token or list of tokens.
    * `default: true`
</Update>

<Update label="May 28, 2025" description="New FAK Order Type">
  We’re excited to introduce a new order type soon to be available to all users: Fill and Kill (FAK). FAK orders behave similarly to the well-known Fill or Kill (FOK) orders, but with a key difference:

  * FAK will fill as many shares as possible immediately at your specified price, and any remaining unfilled portion will be canceled.
  * Unlike FOK, which requires the entire order to fill instantly or be canceled, FAK is more flexible and aims to capture partial fills if possible.
</Update>

<Update label="May 15, 2025" description="Increased API Rate Limits">
  All API users will enjoy increased rate limits for the CLOB endpoints.

  * CLOB - /books (website) (300req - 10s / Throttle requests over the maximum configured rate)
  * CLOB - /books (50 req - 10s / Throttle requests over the maximum configured rate)
  * CLOB - /price (100req - 10s / Throttle requests over the maximum configured rate)
  * CLOB markets/0x (50req / 10s - Throttle requests over the maximum configured rate)
  * CLOB POST /order - 500 every 10s (50/s) - (BURST) - Throttle requests over the maximum configured rate
  * CLOB POST /order - 3000 every 10 minutes (5/s) - Throttle requests over the maximum configured rate
  * CLOB DELETE /order - 500 every 10s (50/s) - (BURST) - Throttle requests over the maximum configured rate
  * DELETE /order - 3000 every 10 minutes (5/s) - Throttle requests over the maximum configured rate
</Update>


Built with [Mintlify](https://mintlify.com).