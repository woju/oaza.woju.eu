<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="html" indent="yes" />
  <xsl:template match="/list">
    <html>
      <head>
        <style type="text/css">
          main {
            display: flex;
            flex-flow: wrap;
            justify-content: space-around;
          }
          main > * {
            width: 12rem;
          }
          main figure {
            text-align: center;
          }
          main img {
            width: 100%;
          }
          main li {
            list-style-type: none;
          }
        </style>
      </head>
      <body>
        <nav>
          <ul>
            <li class="parent"><a href="..">../</a></li>
            <xsl:apply-templates select="directory" />
          </ul>
        </nav>
        <main>
          <xsl:apply-templates select="file" />
        </main>
      </body>
    </html>
  </xsl:template>

  <xsl:template match="directory">
    <li><a href="{.}"><xsl:value-of select="." />/</a></li>
  </xsl:template>

  <xsl:template match="file">
    <figure><a href="{.}">
      <img src="{.}" style="width: "/>
      <figcaption><xsl:value-of select="." /></figcaption>
    </a></figure>
  </xsl:template>
</xsl:stylesheet>

<!-- vim: set ts=2 sts=2 sw=2 et : -->
