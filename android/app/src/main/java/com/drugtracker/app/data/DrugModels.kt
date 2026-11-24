package com.drugtracker.app.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DrugFeed(
    @SerialName("generated_at") val generatedAt: String = "",
    val counts: FeedCounts = FeedCounts(),
    val drugs: List<DrugRecord> = emptyList(),
)

@Serializable
data class FeedCounts(
    val total: Int = 0,
    val ema: Int = 0,
    val tlv: Int = 0,
    @SerialName("nt_radet") val ntRadet: Int = 0,
)

@Serializable
data class DrugRecord(
    val id: String,
    @SerialName("drug_name") val drugName: String,
    @SerialName("active_substance") val activeSubstance: String = "",
    @SerialName("atc_code") val atcCode: String = "",
    @SerialName("therapeutic_area") val therapeuticArea: String = "",
    @SerialName("latest_date") val latestDate: String = "",
    @SerialName("latest_update_type") val latestUpdateType: String = "new_drug",
    @SerialName("sources_present") val sourcesPresent: List<String> = emptyList(),
    val events: List<RegulatoryEvent> = emptyList(),
)

@Serializable
data class RegulatoryEvent(
    val source: String,
    val date: String = "",
    @SerialName("update_type") val updateType: String = "new_drug",
    val status: String = "",
    val title: String = "",
    val indication: String = "",
    val summary: String = "",
    val url: String = "",
)

enum class SourceFilter(val label: String, val code: String?) {
    ALL("All Sources", null),
    EMA("EMA", "EMA"),
    TLV("TLV", "TLV"),
    NT_RADET("NT-rådet", "NT_RADET"),
}

enum class UpdateTypeFilter(val label: String, val code: String?) {
    ALL("All Updates", null),
    NEW_DRUG("New Drug", "new_drug"),
    NEW_INDICATION("New Indication", "new_indication"),
}

enum class AtcGroupFilter(val label: String, val prefix: String?) {
    ALL("All ATC", null),
    L("L · Oncology / Immuno", "L"),
    J("J · Antiinfectives", "J"),
    A("A · Alimentary / Metab", "A"),
    B("B · Blood", "B"),
    C("C · Cardiovascular", "C"),
    N("N · Nervous System", "N"),
    R("R · Respiratory", "R"),
}
