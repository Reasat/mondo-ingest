# Mapping progress report
| Ontology                                         | Tot terms   | Tot excluded   | Tot deprecated   | Tot deprecated unmapped   | Tot mappable _(!excluded, !deprecated)_   | Tot mapped _(mappable)_   | Tot unmapped _(mappable)_   | % unmapped _(mappable)_   |
|:-------------------------------------------------|:------------|:---------------|:-----------------|:--------------------------|:------------------------------------------|:--------------------------|:----------------------------|:--------------------------|
| [ICD10WHO](./unmapped_icd10who.md)               | 12,542      | 0              | 0                | 0                         | 12,542                                    | 209                       | 12,333                      | 98.3%                     |
| [ICD10CM](./unmapped_icd10cm.md)                 | 97,903      | 16,225         | 0                | 0                         | 81,678                                    | 2,062                     | 79,616                      | 97.5%                     |
| [ICD11FOUNDATION](./unmapped_icd11foundation.md) | 57,874      | 0              | 5,775            | 5,773                     | 52,099                                    | 4,594                     | 47,505                      | 91.2%                     |
| [NCIT](./unmapped_ncit.md)                       | 203,691     | 181,107        | 5,495            | 5,489                     | 17,089                                    | 3,812                     | 13,277                      | 77.7%                     |
| [ORDO](./unmapped_ordo.md)                       | 15,841      | 6,391          | 1,468            | 1,293                     | 9,450                                     | 9,376                     | 74                          | 0.8%                      |
| [DOID](./unmapped_doid.md)                       | 14,532      | 2,691          | 2,511            | 2,490                     | 11,840                                    | 11,826                    | 14                          | 0.1%                      |
| [OMIM](./unmapped_omim.md)                       | 30,123      | 19,738         | 1,383            | 1,336                     | 9,006                                     | 9,002                     | 4                           | 0.0%                      |

`Ontology`: Name of ontology  
`Tot terms`: Total terms in ontology  
`Tot excluded`: Total terms Mondo has excluded from mapping / integrating  
`Tot deprecated`: Total terms that the ontology source itself has deprecated  
`Tot mappable (!excluded, !deprecated)`: Total mappable candidates for Mondo; all terms that are not excluded or 
deprecated.  
`Tot mapped (mappable)`: Total mapped terms (that are mappable in Mondo). Includes exact, broad, and narrow mappings.  
`Tot unmapped (mappable)`: Total unmapped terms (that are mappable in Mondo)  
`% unmapped (mappable)`: % unmapped terms (that are mappable in Mondo)

To run the workflow that creates this data, refer to the [workflows documentation](../developer/workflows.md).