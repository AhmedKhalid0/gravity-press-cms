# GravityPress GraphQL API Developer Reference

Base GraphQL Endpoint: `/graphql`  
Interactive GraphiQL Explorer: Available in browser at `http://127.0.0.1:8098/graphql`  
Specification: GraphQL over HTTP (POST)  

---

## 1. Overview

GravityPress uses **Strawberry GraphQL** to expose a type-safe schema. Clients can request exact fields, eliminating over-fetching for mobile apps and single-page applications.

---

## 2. Query Examples

### 2.1 Fetch Compact Article Feed (with Author Info)
```graphql
query GetPublishedArticles {
  articles(limit: 5, offset: 0) {
    title
    slug
    date
    category
    readingTimeMinutes
    excerpt
    featuredImage
    author {
      name
      role
      avatar
    }
  }
}
```

### 2.2 Query Article by Slug with Rendered HTML & TOC
```graphql
query GetArticleDetail {
  article(slug: "cloud-native-microservices-python-314") {
    title
    date
    category
    tags
    wordCount
    readingTimeMinutes
    htmlContent
    tocHtml
    author {
      name
      email
    }
  }
}
```

### 2.3 Search Articles via In-Memory BM25 Index
```graphql
query SearchArticles {
  searchArticles(query: "Cloudflare", limit: 5) {
    title
    slug
    category
    score
    snippet
  }
}
```

### 2.4 Query Site Metadata & Telemetry
```graphql
query GetSiteMetadata {
  siteMetadata {
    title
    tagline
    engine
    version
    totalArticles
    primaryAuthor
  }
}
```
