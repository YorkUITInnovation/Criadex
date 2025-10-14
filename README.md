<h1><img src="/.github/images/cria-llama.png" alt="Criadex Logo" height="35" style="margin-bottom: -5px; margin-right: 2px">Criadex</h1>

A semantic search engine developed by [UIT Innovation](https://github.com/YorkUITInnovation) at [York University](https://yorku.ca/) with a targetted focus on generative AI for higher education.

## 🎯 Purpose

Criadex is an AI-powered search engine designed to apply a modern approach to semantic-based document search using vector databases. 
It can easily be integrated into any application to leverage intelligent document searching.

## Local Development

To run this service locally for development, follow these steps.

1.  **Configure Environment:**
    Create a `.env` file in the root of the project. This file is required to connect to the necessary backend services like MySQL and Elasticsearch.

    ```
    # Criadex API Settings
    APP_API_MODE=TESTING
    APP_API_PORT=25574

    # MySQL Credentials
    MYSQL_HOST=127.0.0.1
    MYSQL_PORT=3306
    MYSQL_USERNAME=root
    MYSQL_PASSWORD=cria
    MYSQL_DATABASE=criabot

    # Elasticsearch Credentials
    ELASTICSEARCH_HOST=127.0.0.1
    ELASTICSEARCH_PORT=9200
    ELASTICSEARCH_USERNAME=elastic
    ELASTICSEARCH_PASSWORD=elastic
    ```

2.  **Install Dependencies:**
    It is recommended to use a Python virtual environment.
    ```sh
    pip install -r requirements.txt
    ```

3.  **Run Tests:**
    ```sh
    pytest
    ```

## 🔧 Maintainers

### YorkU IT Innovation

- Isaac Kogan
- Patrick Thibaudeau
- Vidur Kalive

See also the list of 3rd-party [contributors](https://github.com/YorkUITInnovation/criadex/graphs/contributors) who have participated in the project.

## 📜 Licensing

This project is licensed under the GNU v3.0 License — See the [LICENSE](LICENSE) project file for details.